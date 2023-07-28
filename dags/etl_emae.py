from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.models import XCom
from airflow.models import Variable
from datetime import datetime, timedelta

QUERY_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS emae (
        fecha DATE,
        valor_emae DECIMAL(16,2),
        sector_emae VARCHAR(100),
        frecuencia VARCHAR(10),
        fecha_proceso VARCHAR(8)
    );
"""

QUERY_CLEAN_FECHA_PROCESO = """
    DELETE FROM emae WHERE fecha_proceso = '{{ ti.xcom_pull(key="fecha_proceso") }}';
"""

# Crea una función para obtener la fecha_proceso y almacenarla en xcom
def get_fecha_proceso(**kwargs):
    if (
        "fecha_proceso" in kwargs["dag_run"].conf
        and kwargs["dag_run"].conf["fecha_proceso"] is not None
    ):
        fecha_proceso = kwargs["dag_run"].conf["fecha_proceso"]
    else:
        fecha_proceso = kwargs["dag_run"].conf.get(
            "fecha_proceso", datetime.now().strftime("%Y-%m-%d")
        )
    kwargs["ti"].xcom_push(key="fecha_proceso", value=fecha_proceso)

defaul_args = {
    "owner": "Lautaro Cavallo",
    "start_date": datetime(2023, 7, 1),
    "retries": 0,
    "retry_delay": timedelta(seconds=5),
}

with DAG(
    dag_id="etl_emae",
    default_args=defaul_args,
    description="ETL de la tabla emae",
    schedule_interval="@daily",
    catchup=False,
) as dag:
    
    # Tareas

    # Tarea para obtener la fecha_proceso y almacenarla en xcom
    get_fecha_proceso_task = PythonOperator(
        task_id="get_fecha_proceso",
        python_callable=get_fecha_proceso,
        provide_context=True,
    )

    # Tarea para crear la tabla emae en la base de datos Redshift
    create_table = SQLExecuteQueryOperator(
        task_id="create_table",
        conn_id="redshift_default",
        sql=QUERY_CREATE_TABLE,
        dag=dag,
    )

    # Tarea para limpiar los datos anteriores con la fecha_proceso actual
    clean_fecha_proceso = SQLExecuteQueryOperator(
        task_id="clean_fecha_proceso",
        sql=QUERY_CLEAN_FECHA_PROCESO,
        conn_id="redshift_default",
    )

    # Tarea para ejecutar el proceso ETL en Spark
    spark_etl_emae = SparkSubmitOperator(
        task_id="spark_etl_emae",
        application=f'{Variable.get("spark_scripts_dir")}/EMAE_ETL_Spark.py',
        conn_id="spark_default",
        driver_class_path=Variable.get("driver_class_path"),
    )

    # Definir el orden de ejecución de las tareas
    get_fecha_proceso_task >> create_table >> clean_fecha_proceso >> spark_etl_emae

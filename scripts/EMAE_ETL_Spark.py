import requests
from datetime import datetime, timedelta
from os import environ as env
from datetime import date
from requests import get

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, from_unixtime, to_date, year

from commons import ETL_Spark
from airflow import settings
from airflow.models import Variable
from airflow.operators.email import EmailOperator

class EMAE_ETL_Spark(ETL_Spark):
    def __init__(self, fecha_proceso=None):
        """
        Constructor de la clase, inicializa la sesión de Spark y las variables de configuración

        Entradas:
            fecha_proceso: Fecha de proceso en formato "aaaa-mm-dd", si no se especifica se toma la fecha actual
        """
        print(
            ">>> [init] Inicializando ETL para datos del Estimador Mensual de Actividad Economica (EMAE)"
        )

        super().__init__("Job EMAE - ETL Spark")

        self.ORIGEN_DATOS = "EMAE"
        self.TABLA_DESTINO = "emae"
        self.COLUMNAS_FINALES = [
            "fecha",
            "valor_emae",
            "sector_emae",
            "frecuencia",
            "fecha_proceso",
        ]

        self.FECHA_PROCESO = (
            fecha_proceso
            if fecha_proceso is not None
            else date.today().strftime("%Y-%m-%d")
        )

    def run(self):
        fecha_proceso = datetime.now().strftime("%Y-%m-%d")
        df = self.extract()
        df_transformed = self.transform(df)
        supera_threshold = self.check_thresholds(df_transformed)

        # Carga los datos solo si no se supera el threshold
        if not supera_threshold:
            self.load(df_transformed)
        else:
            print(">>> [ALERTA] Se ha superado el threshold. No se cargarán los datos.")
            self.send_alert()

    def check_thresholds(self, df):
        """
        Verifica los thresholds en el DataFrame df.

        Retorna True si algún threshold se supera, de lo contrario False.
        """
        # Obtén los límites de los thresholds desde las Variables de Airflow
        threshold_valor_emae = Variable.get("emae_threshold_valor", default_var=1000)

        # Verifica si algún valor_emae es mayor que el umbral
        supera_threshold = df.filter(col("valor_emae") > threshold_valor_emae).count() > 0

        return supera_threshold

    def send_alert(self):
        """
        Envía un correo electrónico de alerta cuando se supera el threshold.
        """
        # Obtén la dirección de correo del destinatario desde la Variable de Airflow
        destinatario = Variable.get("alerta_destinatario", default_var="destinatario@example.com")

        # Crea un mensaje de alerta descriptivo con los detalles pertinentes
        mensaje_alerta = (
            "ALERTA: Se ha superado el threshold en la tabla emae.\n"
            "Fecha de proceso: {}\n"
            "Threshold valor_emae: {}\n"
            "Consulta los datos para tomar medidas.\n"
        ).format(self.FECHA_PROCESO, Variable.get("emae_threshold_valor", default_var=1000))

        send_alert_task = EmailOperator(
            task_id="send_alert_task",
            to=[destinatario],
            subject="Alerta de Threshold EMAE",
            html_content=mensaje_alerta,
            trigger_rule="all_done",
        )
        send_alert_task.execute(context={})
    def extract(self):
        """
        Extrae datos de la API

        Ejemplo generado a partir de: https://apis.datos.gob.ar/series/api/series/?metadata=full&collapse=month&collapse_aggregation=avg&ids=11.3_CMMR_2004_M_10,11.3_VMASD_2004_M_23,11.3_VMATC_2004_M_12,11.3_VIPAA_2004_M_5&limit=5000&start=0
        """
        print(f">>> [E] Extrayendo datos de la API del {self.ORIGEN_DATOS}...")

        # Extrae datos de la API
        URL_API = "https://apis.datos.gob.ar/series/api/series/?metadata=full&collapse=month&collapse_aggregation=avg&ids=11.3_CMMR_2004_M_10,11.3_VMASD_2004_M_23,11.3_VMATC_2004_M_12,11.3_VIPAA_2004_M_5&limit=5000&start=0"
        response = get(URL_API)
        response_data = response.json()

        datos = response_data["data"]
        frecuencia = response_data["meta"][0]["frequency"]  # "month"

        # Obtiene nombre de las columnas
        columna_0 = "fecha"
        columna_1 = response_data["meta"][1]["field"]["title"]
        columna_2 = response_data["meta"][2]["field"]["title"]
        columna_3 = response_data["meta"][3]["field"]["title"]
        columna_4 = response_data["meta"][4]["field"]["title"]

        columnas = [
            columna_0,
            columna_1,
            columna_2,
            columna_3,
            columna_4,
        ]

        # Crea dataframe de Spark
        df_crudo = self.spark.createDataFrame(datos, columnas)

        df = df_crudo.withColumn("frecuencia", lit(frecuencia))

        return df

    def transform(self, df_original):
        """
        Transforma los datos
        """
        print(f">>> [T] Transformando datos del {self.ORIGEN_DATOS}...")

        df_1 = df_original.select(
            col(df_original.schema.fields[0].name),
            col(df_original.schema.fields[1].name).alias("valor_emae"),
            lit(df_original.schema.fields[1].name).alias("actividad_emae"),
            col(df_original.schema.fields[5].name).alias("frecuencia"),
        )
        df_2 = df_original.select(
            col(df_original.schema.fields[0].name),
            col(df_original.schema.fields[2].name).alias("valor_emae"),
            lit(df_original.schema.fields[2].name).alias("actividad_emae"),
            col(df_original.schema.fields[5].name).alias("frecuencia"),
        )
        df_3 = df_original.select(
            col(df_original.schema.fields[0].name),
            col(df_original.schema.fields[3].name).alias("valor_emae"),
            lit(df_original.schema.fields[3].name).alias("actividad_emae"),
            col(df_original.schema.fields[5].name).alias("frecuencia"),
        )
        df_4 = df_original.select(
            col(df_original.schema.fields[0].name),
            col(df_original.schema.fields[4].name).alias("valor_emae"),
            lit(df_original.schema.fields[4].name).alias("actividad_emae"),
            col(df_original.schema.fields[5].name).alias("frecuencia"),
        )

        df = (
            df_1.union(df_2)
            .union(df_3)
            .union(df_4)
            .withColumn("fecha_proceso", lit(self.FECHA_PROCESO))
        )

        return df

    def load(self, df_final):
        """
        Carga los datos transformados en Redshift
        """
        print(">>> [L] Cargando datos en Redshift...")

        # agrega columna fecha_proceso
        df_final = df_final.withColumn("fecha_proceso", lit(self.FECHA_PROCESO))

        df_final.write \
            .format("jdbc") \
            .option("url", env['REDSHIFT_URL']) \
            .option("dbtable", f"{env['REDSHIFT_SCHEMA']}.users") \
            .option("user", env['REDSHIFT_USER']) \
            .option("password", env['REDSHIFT_PASSWORD']) \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()
        
        print(">>> [L] Datos cargados exitosamente")

if __name__ == "__main__":
    print("Corriendo script")
    etl = EMAE_ETL_Spark()
    etl.run()

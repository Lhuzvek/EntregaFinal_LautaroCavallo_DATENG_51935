# EntregaFinal_LautaroCavallo_DATENG_51935

 Paso 1: Descarga los archivos necesarios

Descarga el archivo .env.

Descarga el archivo docker-compose.yml.

Crea la carpeta DAG y descarga el archivo "etl_emae".

Crea la carpeta SCRIPT y descarga los archivos "commons" y "EMAE_ETL_spark"

Paso 2: Descarga las imágenes de Airflow y Spark

Ejecuta los siguientes comandos en la terminal para descargar las imágenes necesarias:

docker-compose pull lucastrubiano/airflow:airflow_2_6_2
docker-compose pull lucastrubiano/spark:spark_3_4_1

Paso 3: Inicia los servicios

Utiliza el siguiente comando para iniciar los servicios y construir los contenedores:

docker-compose up --build

Paso 4: Accede a Airflow

Una vez que los servicios estén levantados acceder a Airflow en http://localhost:8080/ desde el navegador web.

Paso 5: Configura las conexiones en Airflow

En la pestaña "Admin" -> "Connections" de Airflow, crea una nueva conexión con los siguientes datos para Redshift:

Conn Id: redshift_default
Conn Type: Amazon Redshift
Host: dirección del host de Redshift
Database: nombre de la base de datos de Redshift
Schema: nombre del esquema de Redshift
User: usuario de Redshift
Password: contraseña de Redshift
Port: 5439
Crea otra nueva conexión con los siguientes datos para Spark:

Conn Id: spark_default
Conn Type: Spark
Host: spark://spark
Port: 7077
Extra: {"queue": "default"}
Paso 6: Configura las variables en Airflow

En la pestaña "Admin" -> "Variables" de Airflow, crea las nuevas variables con los siguientes datos:

Key: driver_class_path
Value: /tmp/drivers/postgresql-42.5.2.jar

Key: spark_scripts_dir
Value: /opt/airflow/scripts

Key: emae_threshold_valor
Value: Valor numérico que representa el límite máximo para la columna "valor_emae" que activará la alerta.

Key: alerta_destinatario
Value: Dirección de correo electrónico del destinatario de las alertas.

Paso 7: Ejecutar el DAG
Ejecuta el DAG llamado etl_emae para iniciar el proceso de extracción, transformación y carga de datos.

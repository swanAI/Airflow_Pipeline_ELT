from airflow import DAG
from datetime import datetime
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from pandas import json_normalize

import json

# La fonction _process_user(ti) est une fonction Python appelée par l'opérateur PythonOperator dans le DAG user_processing. Cette fonction extrait les informations de l'utilisateur à partir de la sortie de la tâche extract_user en utilisant le concept XCom.
# La fonction utilise la méthode xcom_pull de l'objet ti (pour "task instance") pour extraire les données utilisateur de la tâche extract_user. Elle utilise ensuite le module json_normalize pour convertir les données en un format tabulaire et les stocke dans un fichier CSV.
# La tâche process_user est créée avec l'opérateur PythonOperator et appelle cette fonction Python _process_user(ti) pour traiter les données de l'utilisateur. Cette tâche suit la tâche extract_user dans le DAG user_processing et dépend donc de la sortie de cette tâche pour s'exécuter.
# xcom est un moyen de stockage de données intégré à Airflow. Il permet de stocker des données entre les tâches d'un DAG et de les récupérer plus tard dans le même DAG ou même dans d'autres DAG. Les données stockées peuvent être de différents types tels que des chaînes de caractères, des numéros, des dictionnaires ou des listes. XCom est utile pour partager des informations entre les tâches d'un DAG et pour communiquer des données entre différents DAGs.
# La fonction json_normalize est utilisée pour normaliser les données JSON en un dataframe pandas. 

def _process_user(ti):
    user = ti.xcom_pull(task_ids="extract_user")
    user = user['results'][0]
    processed_user = json_normalize({
        'firstname': user['name']['first'],
        'lastname': user['name']['last'],
        'country': user['location']['country'],
        'username': user['login']['username'],
        'password': user['login']['username'],
        'email': user['email']})
    processed_user.to_csv('/tmp/processed_user.csv', index=None, header=False)


#la fonction _store_user() est utilisée pour enregistrer les données utilisateur traitées dans un fichier CSV dans une table de base de données PostgreSQL à l'aide du hook PostgresHook
def _store_user():
    hook = PostgresHook(postgres_conn_id='postgres')
    hook.copy_expert(sql="COPY users FROM stdin WITH DELIMITER as ','",
                     filename='/tmp/processed_user.csv'
    )

# start_date(Début planification DAG)
# schedule_interval(Intervalle de planification qui determine fréquence DAG exécution)
# Si catchup=False, le DAG ne rattrapera pas les tâches manquées et commencera simplement à exécuter les tâches à partir de la date de début de planification.

with DAG(dag_id='user_processing', start_date=datetime(2023, 4, 26), 
        schedule_interval='@daily', catchup=False) as dag:
    
    # La 1ere tâche définie dans ce DAG est un objet PostgresOperator appelé "create_table".
    # Cette tâche est destinée à créer une table de base de données dans PostgreSQL.

    create_table = PostgresOperator(
        task_id='create_table',
        postgres_conn_id='postgres',
        sql='''
            CREATE TABLE IF NOT EXISTS users (
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                country TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL
            );
        ''')

    # La 2éme tache (SENSOR) consiste à vérifier si API est disponible ou non
    #  en interrogeant l'URL de l'API (définie dans le paramètre endpoint) à l'aide d'une connexion HTTP (définie dans le paramètre http_conn_id).
    # attend qu'une URL soit disponible ou qu'une réponse HTTP spécifique soit retournée.

    is_api_available= HttpSensor(
        task_id='is_api_available',
        http_conn_id='user_api',
        endpoint='api/')

    # La 3éme tache consiste à extraires les données utilisateurs de APi
    # endpoint c'est URL de l'API qui est est spécifiée dans le paramètre endpoint et la méthode HTTP utilisée pour l'appel est définie dans le paramètre method (ici, 'GET').
    # method='GET' sert à obtenir les données de Api  
    # response_filter sert extraire les données utilisateur et transformer le format en Json
    # log_response est utilisé pour enregistrer la réponse de l'API dans les journaux du DAG pour le débogage et la vérification
    extract_user = SimpleHttpOperator(
        task_id='extract_user',
        http_conn_id='user_api',
        endpoint='api/', 
        method='GET',
        response_filter=lambda response: json.loads(response.text),
        log_response=True)
    
    # Appeler la fonction _process_user
    process_user = PythonOperator(
        task_id='process_user',
        python_callable=_process_user
    )
    # Appeler la fonction _process_user
    store_user = PythonOperator(
        task_id='store_user',
        python_callable=_store_user
    )


# Définir les dépendances entres les tasks 

create_table >> is_api_available >> extract_user >> process_user >> store_user
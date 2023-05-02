from airflow import DAG, Dataset
from airflow.decorators import task
from datetime import datetime

#Définir URI (Path pour accéder aux données) dans objet Dataset
my_file = Dataset("/tmp/my_file.txt")
#Définir URI (Path pour accéder aux données) dans objet Dataset
my_file_2 = Dataset("/tmp/my_file_2.txt")

# ne pas définir interval mais dataset pour etre consommé
# pour ajouter plusieur fichiers au scheduler.il suffit de mettre les fichiers dans la liste 
with DAG(dag_id='consumer',
         schedule=[my_file, my_file_2],
         start_date=datetime(2023, 4, 27),
         catchup=False):
        
        
         @task
         def read_dataset():
            with open(my_file.uri, "r") as f:
                print(f.read())
        
         read_dataset()
         
         


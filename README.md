# EXAM
Codigo en python para la extraccion de registros de la pagina metroscubicos
## Requisitos minimos
  * Python 3.0 o superior instalado
  * PIP instalado y ligado al PATH de python3
  * Permisos de lectura y escritura desde el path donde se ejecute el script (necesario para crear y modificar la base de datos)
  * Conexion a internet para descargar los registros
## Instalacion de dependencias
Este proyecto tiene dependencias con requests y geopy por lo cual se deben instalar con pip
para instalar todos las dependencias con la herramienta pip se ocupa el siguiente comando:
```console
pip3 install -r requirements.txt
```
## Ejecucion
El unico parametro que recibe el script "adventure.py" es el numero de casas a descargar, no es obligatorio si se ejecuta se tomara el valor default que es 150
```console
python3 adventure.py [numero de casas]
```
### Ejemplo sin parametro
Este ejemplo descargara a la base de datos "exam.db" 150 casas desde metroscubicos
```console
python3 adventure.py
```
### Ejemplo sin parametro
Este ejemplo descargara a la base de datos "exam.db" 10 casas desde metroscubicos
```console
python3 adventure.py 10
```
Si se ejecuta correctamente se desplegara una barra de progreso indicando el porcentaje de descarga de la informacion
<img width="727" alt="Captura de Pantalla 2021-07-23 a la(s) 5 25 23 a m" src="https://user-images.githubusercontent.com/4644454/126769566-3c6893d1-1c2e-4711-98ee-c99836c60c2a.png">

Y al concluir mostrara el siguiente mensaje, indicando cuantas casas se descargaron
<img width="731" alt="Captura de Pantalla 2021-07-23 a la(s) 5 25 56 a m" src="https://user-images.githubusercontent.com/4644454/126769622-df360883-a22b-496a-83b0-ae231cb652d5.png">
## Consideraciones
  * El tiempo de ejecucion puede ser lento en conexiones de internet de baja velocidad
  * Puede ser que se bloquee la conexion a metroscubicos por la cantidad de peticiones y la velocidad, en ese caso el codigo esta programado para parar y esperar 1 segundo luego continuara descargando
  * Tengo cronometrado el tiempo para 150 registros en aproximadamente 2 minutos

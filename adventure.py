#Importacion de modulos
import threading
import sqlite3
from typing import Collection, Text, Tuple
from geopy.geocoders import Nominatim
import requests
import traceback
import hashlib
import json
import re
import sys
import time

#Constantes globales que se ocuparan en el programa
__NUM_HILOS:int = 4 #Cantidad de hilos a utilizar para la extraccion de datos
__BASE_HOUSES_URL:str = "https://casa.metroscubicos.com/" #Base URL Constante para cada casa
__LENGTH_BASE_HOUSES_URL:int = len(__BASE_HOUSES_URL) #Longitud de la Base URL

#Variables globales que se ocuparan en el programa
processedHouses:int = 0 #Cantidad de casas procesadas

#Clase Picture, la cual sirve para almacenar una foto
class Picture(object):
    __id:int #El id de la foto en la base de datos
    attachment:bytes #El adjunto en su representacion binaria
    type:str #El tipo de dato del adjunto (mimetype)
    def __init__(self, id:int, attachment:bytes, type:str)->None:
        self.__id = id
        self.attachment = attachment
        self.type = type
    '''
        Esta funcion retorna el ID de la foto
        @return int el id de la foto
    '''
    def getID(self)->int:
        return self.__id
#Esta clase contiene los metodos necesarios para el manejo de las fotos en la base de datos
class PictureDB(object):
    '''
        Este metodo inserta una foto en la base de datos
        @param picture Picture la foto a insertar
        @param con sqlite3.Connection la conexion a la base de datos
        @return int un entero que contiene el id de la foto en la base de datos, despues de insertarla, en caso de error retorna un numero negativo
    '''
    @staticmethod
    def insertPicture(picture:Picture, con:sqlite3.Connection)->int:
        try:
            cursor:sqlite3.Cursor = con.cursor() #Creamos un cursor a la base de datos
            cursor.execute("INSERT INTO picture (attachment,type) VALUES (?,?)",(picture.attachment,picture.type)) #Realizamos la query para insertar
            con.commit() #Hacemos un commit, ya que lo anterior se ejecuta en una Transaccion
            return cursor.lastrowid #Obtenemos el ID de la imagen recien insertada (se utiliza un auto increment, por ello hay que extraerlo asi) y lo retornamos
        except:
            traceback.print_exc()
            return -1 #Si falla algo retornamos -1
#Esta clase sirve para almacenar una direccion
class Address(object):
    __id:int #El id de la direccion en la base de datos
    name:str #El nombre de la direccion (Como se ve publicamente)
    number:int #El numero del domicilio
    street:str #La calle
    settlement:str #El asentamiento o colonia
    town:str #La ciudad o delegacion
    county:str #El condado o municipio
    state:str #El estado
    latitude:float #La latitud de la direccion
    longitude:float #La longitud de la direccion
    
    def __init__(self, id:int, name:str, number:int, street:str, settlement:str, town:str, county:str, state:str, latitude:float, longitude:float)->None:
        self.__id = id
        self.name = name
        self.number = number
        self.street = street
        self.settlement = settlement
        self.town = town
        self.county = county
        self.state = state
        self.latitude = latitude
        self.longitude = longitude
    '''
        Este metodo trata de rellenar los campos vacios utilizando una herramienta llamada Nominatum
    '''
    def fillWithNominatum(self)->None:
        try:
            #Se indica un nombre del agente para hacer la consulta, esto es obligatorio
            geolocator = Nominatim(user_agent="EXAM")
            #Se obtiene la direccion
            location = geolocator.reverse(str(self.latitude)+","+str(self.longitude))
            if self.name is None:
                self.name = location.address
            arrAddress:dict[str,any] = location.raw['address']
            #Aqui extraigo la direccion del objeto en partes, siempre pregunto si existe porque no todos los parametros van a aparecer siempre
            if self.number is None:
                if('house_number' in arrAddress):
                    self.number = int(arrAddress['house_number'])
            if self.street is None:
                if('road' in arrAddress):
                    self.street = arrAddress['road']
                elif 'street' in arrAddress:
                    self.street = arrAddress['street']
            if self.settlement is None:
                if('city_district' in arrAddress):
                    self.settlement = arrAddress['city_district']
                elif('neighbourhood' in arrAddress):
                    self.settlement = arrAddress['neighbourhood']
            if self.town is None:
                if('town' in arrAddress):
                    self.town = arrAddress['town']
                elif 'city' in arrAddress:
                    self.town = arrAddress['city']
            if self.county is None:
                if 'county' in arrAddress:
                    self.county = arrAddress['county']
                else:
                    self.county = self.town
            if self.state is None:
                if 'state' in arrAddress:
                    self.state = arrAddress['state']
                else:
                    self.state = self.county
        except:
            pass
    '''
        Esta funcion retorna el ID del objeto en la base de datos
        @return int el id de la foto
    '''
    def getID(self)->int:
        return self.__id
    
    '''
        Esta funcion retorna un string con todos los parametros convertidos a formato JSON
        @return str el JSON resultante
    '''
    def toJSON(self)->str:
        return json.dumps(self.toDictionary())

    '''
        Esta funcion retorna un diccionario con los parametros del objeto, y con su nombre como clave
        @return dict[str,any] el diccionario resultante
    '''
    def toDictionary(self)->dict[str,any]:
        dictionary:dict[str,any] = {}
        dictionary["id"] = self.__id
        dictionary["name"] = self.name
        dictionary["number"] = self.number
        dictionary["street"] = self.street
        dictionary["settlement"] = self.settlement
        dictionary["town"] = self.town
        dictionary["county"] = self.county
        dictionary["state"] = self.state
        dictionary["coordinates"] = {}
        dictionary["coordinates"]["latitude"] = self.latitude
        dictionary["coordinates"]["longitude"] = self.longitude
        return dictionary

#Esta clase contiene los metodos necesarios para tratar las direcciones en la base de datos
class AddressDB(object):
    '''
        Este metodo inserta una direccion a la base de datos
        @param address Address la direccion a insertar
        @param con sqlite3.Connection la conexion a la base de datos
        @return int un entero con el id de la direccion en la base de datos, o un numero negativo en caso de error
    '''
    @staticmethod
    def insertAddress(address:Address, con:sqlite3.Connection)->int:
        try:
            cursor:sqlite3.Cursor = con.cursor()
            cursor.execute("INSERT INTO address (name,number,street,settlement,town,county,state,latitude,longitude) VALUES (?,?,?,?,?,?,?,?,?)",(address.name,address.number,address.street,address.settlement,address.town,address.county,address.state,address.latitude,address.longitude))
            con.commit()
            return cursor.lastrowid
        except:
            traceback.print_exc()
            return -1

#Esta clase sirve para almacenar una comodidad en la base de datos
class Amenitie(object):
    __id:int #El id de la comodidad en la base de datos
    text:str #El texto de la comodidad
    md5Hash:str #El hash de la comodidad (Sirve para garantizar que sean unicas y facilitar el trabajo de la base de datos)
    
    def __init__(self, id:int, text:str, md5Hash:str)->None:
        self.__id = id
        self.text = text
        self.md5Hash = md5Hash

    '''
        Esta funcion retorna el ID del objeto en la base de datos
        @return int el id de la foto
    '''
    def getID(self)->int:
        return self.__id
    
    '''
        Esta funcion retorna un string con todos los parametros convertidos a formato JSON
        @return str el JSON resultante
    '''
    def toJSON(self)->str:
        return json.dumps(self.toDictionary())

    '''
        Esta funcion retorna un diccionario con los parametros del objeto, y con su nombre como clave
        @return dict[str,any] el diccionario resultante
    '''
    def toDictionary(self)->dict[str,any]:
        dictionary:dict[str,any] = {}
        dictionary["id"] = self.__id
        dictionary["text"] = self.text
        dictionary["md5Hash"] = self.md5Hash
        return dictionary
        
#Esta clase sirve para almacenar una casa
class House(object):
    __id:int #El id de la casa en la base de datos
    propertyName:str #El nombre de la propiedad (titulo de la publicacion)
    URL:str #La URL de la publicacion
    price:float #El precio de la casa
    address:Address #La direccion de la casa
    description:str #La descripcion de la publicacion
    amenities:list[Amenitie] #Las comodiades listadas en la publicacion
    size:int #Tamanio de la casa en m^2
    firstPicture:Picture #Primer foto de la casa en la galeria de la publicacion
    def __init__(self,id:int, propertyName:str, URL:str, price:float, address:Address, description:str, amenities:list[str],size:int,firstPicture:Picture)->None:
        self.__id = id
        self.propertyName = propertyName
        self.URL = URL
        self.price = price
        self.address = address
        self.description = description
        self.amenities = amenities
        self.size = size
        self.firstPicture = firstPicture
    
    '''
        Esta funcion retorna el ID del objeto en la base de datos
        @return int el id de la foto
    '''
    def getID(self)->int:
        return self.__id
    
    '''
        Esta funcion retorna un string con todos los parametros convertidos a formato JSON
        @return str el JSON resultante
    '''
    def toJSON(self)->str:
        return json.dumps(self.toDictionary())

    '''
        Esta funcion retorna un diccionario con los parametros del objeto, y con su nombre como clave
        @return dict[str,any] el diccionario resultante
    '''
    def toDictionary(self)->dict[str,any]:
        dictionary:dict[str,any] = {}
        dictionary["id"] = self.__id
        dictionary["url"] = self.URL
        dictionary["propertyName"] = self.propertyName
        dictionary["price"] = self.price
        dictionary["address"] = self.address.toDictionary()
        dictionary["description"] = self.description
        dictionary["amenities"] = []
        for amenitie in self.amenities:
            dictionary["amenities"].append(amenitie.toDictionary())
        dictionary["size"] = self.size
        dictionary["firstPicture"] = self.firstPicture.getID()
        return dictionary

#Esta clase contiene los metodos necesarios para manejar las comodidades en la base de datos
class AmenitieDB(object):
    '''
        Esta funcion busca una comodidad en la base de datos por su id
        @param id int El id de la comodidad
        @param con sqlite3.Connection La conexion a la base de datos
        @return Amenitie La comodidad encontrada en la base de datos, None si no se encontro
    '''
    @staticmethod
    def getAmenitieById(id:int,con:sqlite3.Connection)->Amenitie:
        try:
            cursor:sqlite3.Cursor = con.cursor()
            cursor.execute("SELECT text,md5Hash FROM amenitie WHERE amenitie_id = ? LIMIT 1", (id,))
            data = cursor.fetchone()
            if data != None:
                return Amenitie(id,data[0],data[1])
            else:
                return None
        except:
            traceback.print_exc()
            return None         
    '''
        Esta funcion busca una comodidad en la base de datos por su hash md5
        @param md5Hash str El hash de la comodidad
        @param con sqlite3.Connection La conexion a la base de datos
        @return Amenitie La comodidad encontrada en la base de datos, None si no se encontro
    '''   
    @staticmethod
    def getAmenitieByMD5Hash(md5Hash:str, con:sqlite3.Connection)->Amenitie:
        try:
            cursor:sqlite3.Cursor = con.cursor()
            cursor.execute("SELECT amenitie_id FROM amenitie WHERE md5Hash = ? LIMIT 1", (md5Hash,))
            data = cursor.fetchone()
            if data != None:
                return AmenitieDB.getAmenitieById(data[0],con)
            else:
                return None
        except:
            traceback.print_exc()
            return None
    '''
        Esta funcion inserta una comodidad en la base de datos
        @param amenitie Amenitie la comodidad a insertar
        @param sqlite3.Connection La conexion a la base de datos
        @return int Un entero que indica el id de la comodidad en la base de datos o un numero negativo en caso de error
    '''
    @staticmethod
    def insertAmenitie(amenitie:Amenitie, con:sqlite3.Connection)->int:
        try:
            cursor:sqlite3.Cursor = con.cursor()
            cursor.execute("INSERT INTO amenitie (text,md5Hash) VALUES (?,?)", (amenitie.text, amenitie.md5Hash))
            con.commit()
            return cursor.lastrowid
        except:
            traceback.print_exc()
            return -1
    '''
        Esta funcion relaciona una comodidad con una casa en la base de datos
        @param amenitie Amenitie la comodidad a relacionar
        @param house House la casa a relacionar
        @param sqlite3.Connection La conexion a la base de datos
        @return int Un entero que indica si se realizo la relacion (1) o un numero negativo en caso de error
    '''
    @staticmethod
    def joinAmenitieAndHouse(amenitie:Amenitie, house:House, con:sqlite3.Connection)->int:
        try:
            cursor:sqlite3.Cursor = con.cursor()
            cursor.execute("INSERT INTO amenities_house (amenitie,house) VALUES (?,?)", (amenitie.getID(), house.getID()))
            con.commit()
            return 1
        except:
            traceback.print_exc()
            return -1

#Esta clase contiene los metodos necesarios para manejar las casas en la base de datos
class HouseDB(object):
    '''
        Esta funcion inserta una casa en la base de datos
        @param house House la casa a insertar
        @param con sqlite3.Connection la conexion a la base de datos
        @return int un entero con el id de la casa en la base de datos, o un numero negativo en caso de error
    '''
    def insertHouse(house:House, con:sqlite3.Connection)->int:
        try:            
            cursor:sqlite3.Cursor = con.cursor()
            addressID:int = AddressDB.insertAddress(house.address,con)
            if(addressID > 0):
                firstPictureID:int = PictureDB.insertPicture(house.firstPicture,con)
                if(firstPictureID > 0):
                    cursor.execute("INSERT INTO house(URL, propertyName, price, address, description, size, firstPicture) VALUES (?,?,?,?,?,?,?)",(house.URL, house.propertyName,house.price,addressID,house.description,house.size,firstPictureID))
                    con.commit()
                    houseID = cursor.lastrowid
                    houseInDB:House = House(houseID, house.propertyName, house.URL, house.price, house.address, house.description, house.amenities, house.size, house.firstPicture)
                    amenitieInDB:Amenitie = None
                    for amenitie in house.amenities:
                        amenitieInDB = AmenitieDB.getAmenitieByMD5Hash(amenitie.md5Hash,con)
                        if amenitieInDB is None:
                            idAmenitie = AmenitieDB.insertAmenitie(amenitie, con)
                            if idAmenitie > 0:
                                amenitieInDB = Amenitie(idAmenitie, amenitie.text, amenitie.md5Hash)
                            else:
                                return -5
                        if AmenitieDB.joinAmenitieAndHouse(amenitieInDB, houseInDB, con) < 0:
                            return -4
                    return houseID
                else:
                    return -3
            else:
                return -2
        except:
            traceback.print_exc()
            return -1
'''
    Esta funcion retorna el contenido de una pagina web
    @param url{str} La url de la pagina web
    @return {str} El contenido de la pagina web
'''
def getHTTPContent(url:str)->str:
    #Debido a la velocidad de las peticiones puede ser que se bloquee, por ello este ciclo sigue haciendo peticiones hasta que obtiene el contenido
    while True:
        try:
            r = requests.get(url)
            return r.text
        except:
            #Se deja descansar un segundo a los intentos
            time.sleep(1)
'''
    Esta funcion retorna el contenido de una etiqueta dentro de un codigo HTML
    @param src{str} El codigo HTML en el cual se buscara la etiqueta
    @param tag{str} La etiqueta a buscar
    @param startPosition{int} La posicion de inicio de la busqueda, default 0
    @param onlyTagParameter{bool} Se ocupa en caso de que se este buscando un atributo dentro de la etiqueta, no su contenido
    @return {Tuple[str,int]} Una tupla que contiene el contenido de la etiqueta y la posicion de la misma dentro del codigo HTML
'''
def getHTMLTagContent(src:str, tag:str, starPosition:int = 0, onlyTagParameter:bool = False)->Tuple[str,int]:
    #La posicion que resulte de la busqueda
    posTag:int = src.find(tag,starPosition)
    #El contenido de la etiqueta
    content:str = ""
    if(posTag != -1):
        #Si existe la etiqueta, entonces le sumo su tamaño
        posTag+=len(tag)
        #La itero mientras siga siendo o la propiedad de una etiqueta "onlyTagParameter = True" o el contenido de una
        while(src[posTag] != "<" and (src[posTag] != "\"" if onlyTagParameter else True)):
            content+=src[posTag]
            posTag+=1
    #Retorno lo obtenido como una tupla
    return content, posTag

'''
    Esta funcion retorna el contenido de una pagina web en forma de una foto (archivo binario)
    @param url{str} La url de la pagina web
    @return {Picture} El contenido de la pagina web en formato de foto
'''
def getPictureFromURL(url:str)->Picture:
    #Para descargar la imagen debo crear un objeto de bytes
    data:bytes = b''
    #Descargo lo que salga de la URL con un stream para no saturar la memoria RAM
    res = requests.get(url, stream=True)
    #Cada chunk lo sumo al objeto de bytes
    for chunk in res.iter_content(chunk_size=1024):
        data+=chunk
    #Creo un objeto de la clase "Picture" con el objeto de bytes y el tipo de la foto
    return Picture(None, data, res.headers["Content-Type"])

'''
    Esta funcion retorna el contenido de un objeto JSON desde un codigo HTML
    @param src{str} El codigo HTML en el cual se buscara el objeto
    @param jsonSTR{str} La parte inicial del objeto a buscar
    @param addBracket{bool} Si se agrega una "{" al inicio del objeto en forma de cadena de texto
    @return {Tuple[dict[str,any],int]} Una tupla que contiene el contenido del JSON en forma de diccionario y la posicion de la misma dentro del codigo HTML
'''
def getJSONObjectFromSourceCode(src:str, jsonSTR:str,addBracket:bool=False)->tuple[dict[str:any],int]:
    #Encuentro el JSON
    posJSON:int = src.find(jsonSTR)
    if addBracket:
        jsonSTR = '{'+jsonSTR
    jsonDecoded:dict[str:any] = None
    if posJSON != -1:
        #Itero hasta que se acabe este segmento del JSON
        jsonText:src = jsonSTR
        #Cuento cuantas llaves se abren sumando 1 y cuantas se cierran restando 1, cuando llega a 0 se que acabe el objeto
        brackets:int = jsonSTR.count("{")-jsonSTR.count("}")
        posJSON+=len(jsonText)
        if(addBracket):
            posJSON-=1
        while brackets > 0:
            jsonText+=src[posJSON]
            if src[posJSON] == '{':
                brackets+=1
            elif src[posJSON] == '}':
                brackets-=1
            posJSON+=1
        #Obtengo el json como un diccionario
        jsonDecoded = json.loads(jsonText)
    return jsonDecoded, posJSON

'''
    Esta funcion retorna un objeto direccion, el cual obtiene desde un codigo HTML
    @param src{str} El codigo fuente HTML del cual se extraera la informacion
    @return {Address} La direccion encontrada en el HTML y si es posible el complemento con Nominatum
'''
def getAddressFromSourceCode(src:str)->Address:
    address:Address = None
    #Defino las propiedades de la direccion
    settlement:str = None
    town:str = None
    county:str = None
    state:str = None
    latitude:float = None
    longitude:float = None
    #Para obtener la direccion ocupo los datos de la descripcion y las coordenadas de la propiedad, las cuales se encuentran en un JSON en el codigo fuente
    #Primero obtengo la direccion desde la pagina 
    jsonObject,posJSON = getJSONObjectFromSourceCode(src,"\"content_rows\":[{\"icon\":{\"id\":\"LOCATION_RE\",\"color\":\"BLACK\",\"size\":\"XSMALL\"},\"title\":{\"text\":", True)
    if(posJSON != -1):
        arrAddress:list[str] = jsonObject['content_rows'][0]['title']['text'].split(",")
        if(len(arrAddress) > 0):
            state = arrAddress[len(arrAddress)-1].strip()
            arrAddress = arrAddress[:-1]
        if(len(arrAddress) > 0):
            county = arrAddress[len(arrAddress)-1].strip()
            arrAddress = arrAddress[:-1]
        if(len(arrAddress) > 0):
            town = arrAddress[len(arrAddress)-1].strip()
            arrAddress = arrAddress[:-1]
        if(len(arrAddress) > 0):
            settlement = arrAddress[len(arrAddress)-1].strip()
            arrAddress = arrAddress[:-1]
    #Ahora obtengo las coordendas desde un JSON en la pagina
    jsonObject,posJSON = getJSONObjectFromSourceCode(src,"\"location\":{\"latitude\":",addBracket=True)
    if(posJSON != -1):
        latitude = float(jsonObject['location']['latitude'])
        longitude = float(jsonObject['location']['longitude'])
    #Ahora creo el objeto Address con toda la informacion
    address = Address(None,None,None, None,settlement, town, county, state,latitude,longitude)
    #Si no son nulas la longitud y latitud, entonces trato de llenar los huecos con Nominatum
    if(address.latitude is not None and address.longitude is not None):
        address.fillWithNominatum()
    return address

'''
    Esta funcion retorna una lista de objetos Amenitie de todas las comodidades que extraiga de un codigo HTML
    @param src{str} El codigo fuente HTML del cual se extraera la informacion
    @return {list[Amenitie]} Las comodidades encontradas
'''
def getAmenitiesFromSourceCode(src:str)->list[Amenitie]:
    #Creo el arreglo de retorno
    amenities:list[Amenitie] = []
    #Para el caso de las comodidades como es un objeto invisible, que se genera dinamicamente en la pagina, tengo que extraerlo de un JSON que contiene toda la informacion de la casa
    jsonDecoded,posJSON = getJSONObjectFromSourceCode(src, "{\"title\":\"Comodidades y equipamiento\"")
    #Si encontro el JSON en el codigo, lo itero
    if posJSON != -1:
        for amenitieJSON in jsonDecoded["attributes"]:
            #Convierto cada una en un objeto de la clase "Amenitie" y las agrego al arreglo
            amenities.append(Amenitie(None,amenitieJSON['values']['value_text']['text'],hashlib.md5(amenitieJSON['values']['value_text']['text'].encode('utf-8')).hexdigest()))
    #Regreso el arreglo final
    return amenities

'''
    Esta funcion retorna un objeto House del cual extrae toda la informacion desde un codigo HTML
    @param src{str} El codigo fuente HTML del cual se extraera la informacion
    @return {House} La casa encontrada
'''
def getHouseFromURL(url:str)->House:
    #Primero obtengo el codigo fuente de la pagina de la casa
    src:str = getHTTPContent(url)
    #Ahora obtengo el nombre de la casa buscando la etiqueta h1 con class u1-pdp-title (la cual es unica para el titulo)
    propertyName, posPropertyName = getHTMLTagContent(src,"<h1 class=\"ui-pdp-title\">")
    #Ahora obtengo el precio de la casa, ya que igual la class "price-tag-fraction" es unica dentro de un span
    strPrice, posPrice = getHTMLTagContent(src, "<span class=\"price-tag-fraction\">")
    #El precio puede tener decimales, asi que elimino las comas que separan cada 3 digitos y lo convierto a flotante
    price:float = 0.0
    if(posPrice != -1):
        price = float(strPrice.replace(",",""))
    #Ahora obtengo la descripcion de la propiedad
    arrDescription, posDescription = getJSONObjectFromSourceCode(src,"{\"id\":\"description\",\"type\":\"description\",\"state\":\"VISIBLE\",\"title\":\"Descripción\",\"content\":\"")
    description:str = ""
    if(posDescription != -1):
        description = arrDescription["content"]
    #Ahora el tamaño total construido de la propiedad (no se especifica si es el tamaño del terreno o el construido)
    strSize, posSize = getHTMLTagContent(src, "<th class=\"andes-table__header andes-table__header--left ui-pdp-specs__table__column ui-pdp-specs__table__column-title\">Superficie construida</th><td class=\"andes-table__column andes-table__column--left ui-pdp-specs__table__column\"><span class=\"andes-table__column--value\">")
    size:int = 0
    if(posSize != -1):
        #Elimino todo lo que no sea un numero entero (tambien la potencia de m^2)
        size = int(re.sub("[^0-9]", "", strSize))
    #Ahora obtengo la primer imagen de la propiedad, este tag se repite N veces acorde a las N fotos de la galeria, por eso solo extraigo el primero y me aseguro que sea una imagen porque tambien hay videos y representaciones 3D
    firstPictureURL, firstPicturePos = getHTMLTagContent(src, "<figure class=\"ui-pdp-gallery__figure\"><img data-zoom=\"", onlyTagParameter=True)
    firstPicture:Picture = None
    if firstPicturePos:
        #Descargo la imagen con otra funcion
        firstPicture = getPictureFromURL(firstPictureURL)
    #Ahora obtengo las comodidades de la casa
    amenities:list[Amenitie] = getAmenitiesFromSourceCode(src)
    #Ahora obtengo la direccion en formato RAW (solo el texto) y un objeto del tipo "Address" que contenga la informacion ordenada
    address = getAddressFromSourceCode(src)
    return House(None,propertyName,url,price,address,description,amenities,size,firstPicture)

'''
    Esta funcion procesa todas las casas de las cuales se le proporcione un URL y las inserta en la base de datos
    @param housesURLs{list[str]} Un arreglo con las url de las casas a procesar
'''
def processHouses(housesURLs:list[str])->None:
    global processedHouses
    con:sqlite3.Connection = sqlite3.connect("exam.db")
    houseURL:str
    for houseURL in housesURLs :
        currentHouse:House = getHouseFromURL(houseURL)
        HouseDB.insertHouse(currentHouse, con)
        processedHouses+=1
    con.close()

'''
    Esta funcion obtiene N urls de casas desde la pagina de metroscubicos
    @param numHouses{int} Un entero N que indica cuantas casas debe buscar
    @return {list[str]} Las url de las primeras N casas encontradas
'''
def getHousesURLs(numHouses:int)->list[str]:
    #Cual es la primer casa de la pagina, se ocupa al solicitar las siguientes paginas
    fromHouse:int = 1
    #Las url de casas recolectadas
    collected = []
    #Mientras no hayamos recolectado las necesarias seguiremos pasando de pagina en pagina
    while(len(collected) < numHouses):
        #Se solicita el codigo fuente de la pagina actual para conseguir las siguientes 48 URLs
        src:str = getHTTPContent("https://inmuebles.metroscubicos.com/casas/venta/_Desde_"+str(fromHouse))
        #Hay 48 casas en cada pagina asi que se aumentan al URL
        fromHouse +=48
        #Se calcula el indice de la primer URL de una casa
        lastIndex:int = src.find(__BASE_HOUSES_URL,0)
        #En esta variable se almacenara la URL de la casa que se esta encontrando actualmente
        currentUrl:str = __BASE_HOUSES_URL
        #Mientras haya coincidencias en la pagina se sigue buscando
        while(lastIndex != -1):
            #Se le suma al indice el tamanio ya conocido de la url base de cada casa
            lastIndex+=__LENGTH_BASE_HOUSES_URL
            #Mientras la url no termine en # o en " se sigue agregando a la url actual
            #Porque todas las url en los link acaban en # luego siguen parametros de seguimiento y estadistica
            #La " es en caso de que cambie ya que aun asi las etiquetas <a tienen que encerrar la URL entre comillas
            while(src[lastIndex] != '#' and src[lastIndex] !="\""):
                currentUrl+=src[lastIndex]
                lastIndex+=1
            #Se agrega al arreglo de URLs obtenidas
            if(currentUrl not in collected):
                collected.append(currentUrl)
            #Se reinicia la url procesada a la base
            currentUrl = __BASE_HOUSES_URL
            #Se consigue el siguiente resultado
            lastIndex = src.find(__BASE_HOUSES_URL,lastIndex)
    #Se retornan las url obtenidas
    return collected[:numHouses]
'''
    Esta funcion inicializa la base de datos creando las estructuras de las tablas
'''
def initDB()->None:
    con:sqlite3.Connection = sqlite3.connect("exam.db")
    cursor:sqlite3.Cursor = con.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS picture (picture_id INTEGER PRIMARY KEY AUTOINCREMENT, attachment BLOB NOT NULL, type TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS address (address_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, number INTEGER, street TEXT, settlement TEXT, town TEXT, county TEXT, state TEXT, latitude REAL, longitude REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS house (house_id INTEGER PRIMARY KEY AUTOINCREMENT, propertyName TEXT NOT NULL, URL TEXT NOT NULL, price REAL NOT NULL, address INTEGER NOT NULL, description TEXT NOT NULL, size INTEGER NOT NULL, firstPicture INT NOT NULL, FOREIGN KEY(address) REFERENCES address(address_id), FOREIGN KEY(firstPicture) REFERENCES picture(picture_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS amenitie (amenitie_id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, md5Hash TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS amenities_house (amenitie INTEGER NOT NULL, house INTEGER NOT NULL, FOREIGN KEY (amenitie) REFERENCES amenitie(amenitie_id), FOREIGN KEY (house) REFERENCES house(house_id) )")
    con.commit()
    con.close()

'''
    Esta funcion crea una barra de progreso en la consola
    @param numHouses{int} el numero total de casas (100% de la barra de progreso)
'''
def generateProgressBar(numHouses:int)->None:
    print("Filling DataBase")
    #Escribimos [] con 100 espacios dentro
    sys.stdout.write("[%s]" % (" " * 100))
    #Enviamos el buffer
    sys.stdout.flush()
    #Regresamos a la posicion inmediatamente despues del "[" 
    sys.stdout.write("\b" * (100+1))
    #La variable del porcentaje anterior para la diferencia
    lastPercentage:int = 0
    #Mientras no se alcance el 100%
    while processedHouses < numHouses:
        #Calculamos el porcentaje actual
        percentage:int = processedHouses*100 // numHouses
        #Si el porcentaje avanzo en algo entonces escribimos la diferencia en guiones
        if percentage > lastPercentage:
            sys.stdout.write("-"*(percentage-lastPercentage))
            sys.stdout.flush()
            lastPercentage = percentage
    #Al acabar debemos representar la ultima diferencia en guiones
    sys.stdout.write("-"*(100-lastPercentage))
    sys.stdout.flush()
    #Terminamos la barra de progreso
    sys.stdout.write("]\n")
    print("Database filled with "+str(numHouses)+" houses :)")

'''
    Cuerpo principal del programa, inicializa los hilos, la barra de progreso y la base de datos, asi como manda a llamar a los metodos necesarios para el procesado de las casas
'''
def main()->None:
    initDB()
    numHouses:int = 150
    #Aqui se busca si hay algun parametro en la entrada del programa y que sea numerico lo cual representaria el numero de casas a buscar
    if(len(sys.argv) == 2 and sys.argv[1].isnumeric()):
        #En caso de que si, se reescribe la variable con el numero del parametro, en caso contrario se deja el default
        numHouses = int(sys.argv[1])
    
    #Ahora se obtienen las N urls de las casa
    housesURLs = getHousesURLs(numHouses)
    #Enviamos la barra de progreso a una tarea asincrona
    progressBarThread:threading.Thread = threading.Thread(target=generateProgressBar,args=(numHouses,))
    progressBarThread.start()
    #Se crea el arreglo de hilos
    threads:list[threading.Thread] = []
    #Se crea un for para lanzar los hilos que buscaran las N casas
    for i in range(0, __NUM_HILOS):
        #Se obtienen el rango de inicio y fin para las casas
        rangeStart:int = (numHouses//__NUM_HILOS)*i
        rangeEnd:int = numHouses if i == __NUM_HILOS-1 else rangeStart + (numHouses//__NUM_HILOS)
        threads.append(threading.Thread(target=processHouses, args=(housesURLs[rangeStart:rangeEnd],)))
        threads[i].start()
    #Nos unimos a los hilos para garantizar que todos acaben y cambiar la barra de progreso a 100%
    for i in range(0, __NUM_HILOS):
        threads[i].join()
    global processedHouses
    #Completamos la barra de progreso
    processedHouses = numHouses

#Mandamos llamar a la funcion main desde el script principal
main()
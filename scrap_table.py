from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import boto3
import uuid


# Espera hasta que la tabla tenga datos reales (y no la fila "Cargando...")
def tabla_cargada(driver):
    filas = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
    if not filas:
        return False
    return "Cargando" not in filas[0].text


def obtener_html(url):
    # Opciones de Chrome para correr en AWS Lambda (sin ventana, sin pantalla)
    options = Options()
    options.binary_location = "/opt/chrome/chrome"  # ruta segun tu imagen Docker
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--single-process")
    options.add_argument("--window-size=1920,1080")

    service = Service("/opt/chromedriver")  # ruta segun tu imagen Docker
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(tabla_cargada)
        return driver.page_source
    finally:
        driver.quit()


def lambda_handler(event, context):
    # URL de la página web que contiene la tabla
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    # Cargar la página con un navegador (la tabla se genera con JavaScript)
    try:
        html = obtener_html(url)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error al acceder a la página web: {str(e)}'
        }

    # Parsear el contenido HTML ya renderizado
    soup = BeautifulSoup(html, 'html.parser')

    # Encontrar la tabla en el HTML
    table = soup.find('table')
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla en la página web'
        }

    # Extraer los encabezados de la tabla
    headers = [header.text.strip() for header in table.find_all('th')]

    # Extraer las filas de la tabla
    rows = []
    for row in table.find('tbody').find_all('tr'):
        cells = row.find_all('td')
        if not cells:
            continue
        # Se omiten columnas sin nombre de encabezado (DynamoDB no acepta claves vacías)
        # y '#', que se genera más abajo al insertar
        fila = {
            headers[i]: cell.text.strip()
            for i, cell in enumerate(cells)
            if i < len(headers) and headers[i] and headers[i] != '#'
        }
        rows.append(fila)

    # Guardar los datos en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('TablaWebScrappingSismos')

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = table.scan()
    with table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(
                Key={
                    'id': each['id']
                }
            )

    # Insertar los nuevos datos
    i = 1
    for row in rows:
        row['#'] = i
        row['id'] = str(uuid.uuid4())  # Generar un ID único para cada entrada
        table.put_item(Item=row)
        i = i + 1

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': rows
    }

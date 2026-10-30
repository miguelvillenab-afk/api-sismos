from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import json

# Poner en True para ver el navegador abierto mientras scrapea
MOSTRAR_NAVEGADOR = False

URL = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"


# Espera hasta que la tabla tenga datos reales (y no la fila "Cargando...")
def tabla_cargada(driver):
    filas = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
    if not filas:
        return False
    return "Cargando" not in filas[0].text


def obtener_html(url):
    options = webdriver.ChromeOptions()
    if not MOSTRAR_NAVEGADOR:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(tabla_cargada)
        return driver.page_source
    finally:
        driver.quit()


def scrapear(url):
    try:
        html = obtener_html(url)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error al acceder a la página web: {e}'
        }

    soup = BeautifulSoup(html, 'html.parser')

    table = soup.find('table')
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla en la página web'
        }

    # Encabezados
    headers = [header.text.strip() for header in table.find_all('th')]
    print("Encabezados:", headers)

    # Filas
    rows = []
    for row in table.find('tbody').find_all('tr'):
        cells = row.find_all('td')
        if not cells:
            continue
        # Mismo criterio que en la versión Lambda: se omiten columnas sin nombre y '#'
        fila = {
            headers[i]: cell.text.strip()
            for i, cell in enumerate(cells)
            if i < len(headers) and headers[i] and headers[i] != '#'
        }
        rows.append(fila)

    # Numerar filas (igual que se hace antes de guardar en DynamoDB)
    for i, row in enumerate(rows, start=1):
        row['#'] = i

    return {
        'statusCode': 200,
        'body': rows
    }


if __name__ == "__main__":
    resultado = scrapear(URL)
    print("statusCode:", resultado['statusCode'])
    if resultado['statusCode'] == 200:
        print(f"Filas obtenidas: {len(resultado['body'])}")
        print(json.dumps(resultado['body'][:5], indent=2, ensure_ascii=False))
    else:
        print(resultado['body'])

import os
import network
import time
import ufirebase as firebase
from machine import Pin
from machine import UART
from esp32_gpio_lcd import GpioLcd
import esp
esp.osdebug(None)
import gc
gc.collect()
try:
  import usocket as socket
except:
  import socket


"""
Parametros inicais
"""
#########################################################################################
input_anterior = ''
lista_cliente = []
#########################################################################################
"""
Funcoes
"""
#########################################################################################  
def web_page():  
  html = """
  <html>
    <head> 
      <title>
      ESP Web Server
      </title> 
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link rel="icon" href="data:,"> 
      <style>
      </style>
    </head>
    <body>
      <h1>
      Fast Buy
      <h2>
      Digite o codigo do produto:
      <h3>
      0 = para finalizar a compra
      9 = para remover um produto da lista
      </h3>
      </h2>
      </h1>
      <form>
        <label for="codigo_barras">Codigo de barras:</label><br>
        <input type="number" name="codigob">
      </form> 
    </body>
  </html>
  """
  return html


def reseta_lista_cliente():
  """
  Reseta a lista de clientes
  """
  global lista_cliente
  lista_cliente = []  
  

def escreve_display(texto):
  """
  Escreve no display ligado ao ESP
  """
  global lcd
  
  lcd.clear()
  lcd.putstr(texto)
 
 
def conecta_wifi(wlan):
  """
  Conecta ao Wifi e ao Firebase, fica travado na funcao ate conectar
  """
  if not wlan.isconnected():
    #escreve_display('Conectando...\nAguarde por favor.')
    print('Conectando...\nAguarde por favor.')
    wlan.connect("CLARO_APT704", "Mateus704")
    while not wlan.isconnected():
      pass

  #Connectando ao firebase
  firebase.setURL("https://teste-a317b-default-rtdb.firebaseio.com/")
  
  #escreve_display('Conectado!')
  print('Conectado!')
  time.sleep_ms(700)


def verifica_preco_lista_cliente():
  """
  Verifica o preco total dos itens do cliente
  """
  global lista_cliente

  if bool(lista_cliente):
    valores_aux = []
    for i in lista_cliente:
      valores_aux.append(list(i.values()))

    valores = []
    for i in valores_aux:
      valores.append(i[0])

    return sum(valores)
  else:
    return 0.0


def get_preco_produto(codigo_produto):
  """
  Faz uma requisicao para saber o preco de determinado produto
  """
  firebase.get('Produtos/' + str(codigo_produto), 'var1', bg=0)
  return firebase.var1
  
 
def get_id_cliente():
  """
  Retorno o Id do cliente
  """
  firebase.get('Clientes/', 'var3', bg=0)
  
  # Nesse caso se o banco de dados estiver vazio, daria erro, por isso a utilizacao do except
  try:
    return(len(firebase.var3))
  except TypeError:
    return 1
  
  
def adciona_lista(codigo_produto):
  """
  Verifica se o produto existe no banco de dados, se sim, adiciona o codigo do produto e seu respectivo preco a lista do cliente
  """
  firebase.get('Produtos/', 'var2', bg=0)
  
  cont = 0
  for i in firebase.var2.keys():
    if i == codigo_produto:
        cont = 1
        break
  
  if cont == 1:
    global lista_cliente
    lista_cliente.append({codigo_produto: get_preco_produto(codigo_produto)})
    #escreve_display('Produto adcionado!')
    print('Produto adcionado!')
  else:
    #escreve_display('Produto inexistente\nNo banco de dados.')
    print('Produto inexistente\nNo banco de dados.')
  
  
def remove_produtos(codigo_produto):
  """
  Remove produto da lista do cliente, com as devidas verificacoes
  """
  global lista_cliente
  # Coloca todos os codigos de produtos em uma lista
  codigos_produtos_aux = []
  for i in lista_cliente:
    codigos_produtos_aux.append(list(i.keys()))

  # Verifica se o produto selecionado esta na lista do cliente, se estiver, o remove
  cont = 0
  for i in range(len(codigos_produtos_aux)):
    if codigos_produtos_aux[i][0] == codigo_produto:
      lista_cliente.pop(i)
      #escreve_display('Produto removido!')
      print('Produto removido!')
      cont = 1
      break
    
  if cont == 0:
    #escreve_display('Este produto nao \nEsta na sua lista.')
    print('Este produto nao \nEsta na sua lista.')


def envia_lista_firebase():
  """
  Envia a lista do cliente ao Firebase
  """
  global lista_cliente
  id_cliente = get_id_cliente()
  
  # Sera enviado ao firebase, o codigo do produto, e sua quantidade comprada
  chaves_aux = []
  for i in lista_cliente:
    chaves_aux.append(list(i.keys()))

  chaves = []
  for i in chaves_aux:
    chaves.append(i[0])

  Lista_de_compras = {}
  for i in chaves:
    Lista_de_compras[i] = chaves.count(i)
  
  firebase.put("Clientes/" + str(id_cliente), Lista_de_compras, bg=0)


def get_web_input():
  """
  """

  global s

  dado_filtrado = False
  while not dado_filtrado:
    try:
  
      conn, addr = s.accept()
      request = conn.recv(1024)
      request = str(request)
      # O motivo do 15 e do 16 eh empirico, analisando o que essa funcao sempre retorna
      posicao_final = request.find("HTTP")
      input_web = request[16:int(posicao_final - 1)]
        
      response = web_page()
      conn.send('HTTP/1.1 200 OK\n')
      conn.send('Content-Type: text/html\n')
      conn.send('Connection: close\n\n')
      conn.sendall(response)
      conn.close()
          
      if request[15].endswith("="):
        if input_web is not ' ' and input_web is not '':
          dado_filtrado = True

    except IndexError:
      pass

  return input_web


def input_scanner(codigo_produto):
  """
  Recebeb o input do scanner, retorna 1 se o atendimento acabou;
  """
  if codigo_produto == '0':
    envia_lista_firebase()
    reseta_lista_cliente()
    print('###################################################')
    return 1
    
  elif codigo_produto == '9':
    global lista_cliente
    # Verifica se a lista do cliente esta vazia
    if bool(lista_cliente):
      # Le novamente o que esta no serial e converte para string
      #uart_input = uart1.read().decode('utf8')
      #escreve_display('Escaneie o produto\nA ser removido.')
      print('Escaneie o produto\nA ser removido.')
      #uart_input = input()
      uart_input = get_web_input()
      
      remove_produtos(uart_input)
    else:
      #escreve_display('lista ja esta vazia')
      print('Sua ja esta vazia.')
      
  else:
    adciona_lista(codigo_produto)


def info_cliente():
  """
  Retorna a informacao do cliente(Id e Valor total dos produtos)
  """
  global lcd
  #Move o cursor para linha 0, coluna 2(terceira)
  #lcd.move_to(0, 2)
  
  #lcd.putstr('Cliente: ' + str(get_id_cliente()) + '\nValor Total: R$' + str(verifica_preco_lista_cliente()))
  print('Cliente: ' + str(get_id_cliente()) + '\nValor Total: R$' + str(verifica_preco_lista_cliente()))
  
  
def inicia_atendimento(wlan):
  """
  Inicia um atendimento, dando boas vindas ao cliente
  """
  global lcd
  
  #Apaga o display e da boas vindas ao cliente
  #lcd.clear()
  #lcd.putstr('Ola! Cliente: ' + str(get_id_cliente()) + '\nBoas compras!' + '\n\nValor Total: R$' + str(verifica_preco_lista_cliente()) + '\nIP:' + wlan.ifconfig()[0])
  print('Ola! Cliente: ' + str(get_id_cliente()) + 'Boas compras!' + 'Valor Total: R$' + str(verifica_preco_lista_cliente()) + 'IP:' + wlan.ifconfig()[0])
#########################################################################################
"""
Execucao
"""
#Instancia o objeto LCD
lcd = GpioLcd(rs_pin=Pin(4), enable_pin=Pin(15), d4_pin=Pin(5), d5_pin=Pin(18), d6_pin=Pin(21), d7_pin=Pin(22), num_lines=4, num_columns=20)

#Instancia o objeto network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Verifica se o ESP32 esta conectado no wifi
if not wlan.isconnected():
  conecta_wifi(wlan)
 
inicia_atendimento(wlan) 

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)
#Loop de execucao
while True:
  
  # Verifica se o ESP32 esta conectado no wifi
  if not wlan.isconnected():
    conecta_wifi(wlan)
  """
  # Cria a conexao UART
  uart1 = UART(2, baudrate=115200)
  # Le o que esta no serial e converte para string
  if uart1.any() > 0:
    #uart_input = uart1.read().decode('utf8')
    led.on()
    uart_input = uart1.read()
    print(uart_input)
  """
  #uart_input = input('\nDigite o codigo do produto: \n0 = para finalizar a compra\n9 = para remover um produto da lista\n')
  print('\nDigite o codigo do produto: \n0 = para finalizar a compra\n9 = para remover um produto da lista\n')
  
  uart_input = get_web_input()
  
  fim_atendimento = input_scanner(uart_input)
  
  if fim_atendimento is 1:
    inicia_atendimento(wlan)
  else:
    info_cliente()
  

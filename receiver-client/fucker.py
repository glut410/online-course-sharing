from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep

import socket  
import json
from queue import Queue
from threading import Thread

HOST = '127.0.0.1' 
PORT = 8001
BUFSIZ =1024
ADDRESS = (HOST, PORT)


def browser_init(url):
    options = Options()
    browser = webdriver.Chrome(chrome_options = options, executable_path='./chromedriver.exe')
    browser.find_element
    return login(browser, init_url=url)


def login(browser, init_url):
    browser.get(init_url)
    browser.refresh()
    return browser


client_type ='Receiver'
message_channel = Queue()
god_cmd = False

def send_data(client, cmd, **kv):
    global client_type
    jd = {}
    jd['COMMAND'] = cmd
    jd['client_type'] = client_type
    jd['data'] = kv
    
    jsonstr = json.dumps(jd)
    print('send: ' + jsonstr)
    client.sendall(jsonstr.encode('utf8'))


def socket_run():
    global message_channel
    global god_cmd
    # client_type = input_client_type()
    client = socket.socket() 
    client.connect(ADDRESS)
    print(client.recv(1024).decode(encoding='utf8'))
    send_data(client, 'CONNECT')
    
    while True:
        if god_cmd:
            break
        heartbeat = 'I am ok'
        send_data(client, 'HEART_BEAT', data=heartbeat)
        msg = client.recv(1024).decode(encoding='utf8')
        if msg != '/fkkOk':
            message_channel.put(msg)
            print(msg)
        sleep(3)
        
    client.close()


def action(browser):
    global message_channel
    global god_cmd
    try:   #Bypass device check.
        sleep(5)
        cross_button = browser.find_element("xpath", "/html/body/div/div/div/div/p")
        browser.execute_script("arguments[0].click();", cross_button)
        sleep(3)
        skip_button = browser.find_element('xpath', '/html/body/div[2]/div/div[3]/span[1]')
        browser.execute_script("arguments[0].click();", skip_button)
        sleep(2)
        waring = browser.find_element('xpath', '/html/body/div/div/div[3]/div/span')
        browser.execute_script("arguments[0].click();", waring)
        sleep(2)
        confirm = browser.find_element('xpath', '/html/body/div[1]/div/div[2]/div/div[2]/div/div[4]')
        browser.execute_script("arguments[0].click();", confirm)
        sleep(2)
        enter = browser.find_element("xpath", '/html/body/div[1]/div/div[10]/div/div/img')
        browser.execute_script("arguments[0].click();", enter)
        sleep(2)
        chat = browser.find_element('xpath', '/html/body/div[1]/div/div[5]/section/ul/li[3]')
        browser.execute_script("arguments[0].click();", chat)
    except Exception as e:
        print(str(e))

    thread = Thread(target=socket_run, args=())
    # 设置成守护线程
    # thread.setDaemon(True)
    thread.start()

    while True:
        while message_channel.qsize() > 0:
            ques = message_channel.get()
            print('I am gonna say: '+ques)
            try:
                textfield = browser.find_element('xpath', '/html/body/div[2]/div[1]/div[2]/div[4]')
                browser.execute_script("arguments[0].click();", textfield)
                sleep(0.5)
                textfield.send_keys(ques)
                send_button = browser.find_element('xpath', '/html/body/div[2]/div[1]/div[2]/p')
                sleep(0.2)
                browser.execute_script("arguments[0].click();", send_button)
                sleep(1)
            except:
                print("omg")

def main():
    with open('./config.json', 'r', encoding='utf8') as file:
        config = json.load(file)
    browser = browser_init(
        url=config['url']
    )
    action(browser)
    

if __name__ == '__main__':
    main()
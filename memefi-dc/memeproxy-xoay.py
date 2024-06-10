import aiohttp
import asyncio
import json
import random
import string
import time
from datetime import datetime
from urllib.parse import unquote
from utils.headers import headers_set
from utils.query import QUERY_USER, QUERY_LOGIN, MUTATION_GAME_PROCESS_TAPS_BATCH, QUERY_BOOSTER, QUERY_NEXT_BOSS
from utils.query import QUERY_TASK_VERIF, QUERY_TASK_COMPLETED, QUERY_GET_TASK, QUERY_TASK_ID, QUERY_GAME_CONFIG

url = "https://api-gw-tg.memefi.club/graphql"

def generate_random_nonce(length=52):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def load_proxy(file_path='proxy.txt'):
    with open(file_path, 'r') as file:
        proxy = file.readline().strip()
    return proxy

async def change_ip():
    change_ip_url = "url change ip"
    async with aiohttp.ClientSession() as session:
        async with session.get(change_ip_url) as response:
            if response.status == 200:
                data = await response.json()
                if data['status'] == 0:
                    print("Đổi IP thành công")
                    return True
                else:
                    print(f"Lỗi khi đổi IP: {data['message']}")
                    return False
            else:
                print(f"Lỗi khi gọi API đổi IP: Trạng thái {response.status}")
                return False

async def check_ip_proxy(proxy):
    retries = 3  
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org?format=json', proxy=f'{proxy}', timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        ip = data.get('ip', 'Unknown')
                        print(f"Địa chỉ IP mới: {ip}")
                        return
                    else:
                        print("Không thể kiểm tra địa chỉ IP mới.")
        except Exception as e:
            print(f"Lỗi khi kiểm tra địa chỉ IP mới: {e}. Thử lại ({attempt + 1}/{retries})...")
            await asyncio.sleep(5) 
    print("Không thể kết nối sau nhiều lần thử.")
            
async def fetch(account_line, proxy):
    max_retries = 3  
    for attempt in range(max_retries):
        try:
            proxy = load_proxy()  
            if not proxy:
                print("Không tìm thấy proxy hợp lệ.")
                continue
        
            with open('query_id.txt', 'r') as file:
                lines = file.readlines()
                raw_data = lines[account_line - 1].strip()

            tg_web_data = unquote(unquote(raw_data))
            query_id = tg_web_data.split('query_id=', maxsplit=1)[1].split('&user', maxsplit=1)[0]
            user_data = tg_web_data.split('user=', maxsplit=1)[1].split('&auth_date', maxsplit=1)[0]
            auth_date = tg_web_data.split('auth_date=', maxsplit=1)[1].split('&hash', maxsplit=1)[0]
            hash_ = tg_web_data.split('hash=', maxsplit=1)[1].split('&', maxsplit=1)[0]

            user_data_dict = json.loads(unquote(user_data))

            url = 'https://api-gw-tg.memefi.club/graphql'
            headers = headers_set.copy()
            data = {
                "operationName": "MutationTelegramUserLogin",
                "variables": {
                    "webAppData": {
                        "auth_date": int(auth_date),
                        "hash": hash_,
                        "query_id": query_id,
                        "checkDataString": f"auth_date={auth_date}\nquery_id={query_id}\nuser={unquote(user_data)}",
                        "user": {
                            "id": user_data_dict["id"],
                            "allows_write_to_pm": user_data_dict["allows_write_to_pm"],
                            "first_name": user_data_dict["first_name"],
                            "last_name": user_data_dict["last_name"],
                            "username": user_data_dict.get("username", "Username không được đặt"),
                            "language_code": user_data_dict["language_code"],
                            "version": "7.2",
                            "platform": "ios"
                        }
                    }
                },
                "query": QUERY_LOGIN
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, proxy=proxy) as response:
                    json_response = await response.json()
                    if 'errors' in json_response:
                        print("Có lỗi trong phản hồi. Đang thử lại...")
                    else:
                        access_token = json_response['data']['telegramUserLogin']['access_token']
                        return access_token, proxy

        except aiohttp.ServerTimeoutError:
            print("❌ Máy chủ hết thời gian phản hồi. Đang thử lại...")

        except Exception as e:
            print(f"❌ Lỗi không mong muốn: {e}. Đang thử lại...")

        ip_changed = await change_ip() 
        if not ip_changed:
            print("Không thể thay đổi IP. Đang thử lại với IP cũ...")
        else:
            print("IP đã được thay đổi. Đang chờ 120 giây trước khi thử lại...")
        await asyncio.sleep(120)  

    print("❌ Đã hết số lần thử lại. Chuyển sang tác vụ tiếp theo.")
    return None, None 



async def check_user(index, proxy):
    proxy = load_proxy()
    if not proxy:
        print("Không tìm thấy proxy hợp lệ.")
        return None, None
    result = await fetch(index + 1, proxy)
    if not result:
        return None

    access_token, proxy = result

    url = "https://api-gw-tg.memefi.club/graphql"

    headers = headers_set.copy()
    headers['Authorization'] = f'Bearer {access_token}'
    
    json_payload = {
        "operationName": "QueryTelegramUserMe",
        "variables": {},
        "query": QUERY_USER
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                if 'errors' in response_data:
                    print(f"❌ Lỗi Query ID Sai")
                    return None
                else:
                    user_data = response_data['data']['telegramUserMe']
                    return user_data, proxy
            else:
                print(response)
                print(f"❌ Lỗi với trạng thái {response.status}, thử lại...")
                return None

async def activate_energy_recharge_booster(index, headers, proxy):
    proxy = load_proxy() 
    if not proxy:
        print("Không tìm thấy proxy hợp lệ.")
        return None, None
    result = await fetch(index + 1, proxy)
    if not result:
        return None

    access_token, proxy = result

    url = "https://api-gw-tg.memefi.club/graphql"

    headers = headers_set.copy()
    headers['Authorization'] = f'Bearer {access_token}'
    
    recharge_booster_payload = {
        "operationName": "telegramGameActivateBooster",
        "variables": {"boosterType": "Recharge"},
        "query": QUERY_BOOSTER
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=recharge_booster_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                if response_data and 'data' in response_data and response_data['data'] and 'telegramGameActivateBooster' in response_data['data']:
                    new_energy = response_data['data']['telegramGameActivateBooster']['currentEnergy']
                    print(f"\nNạp năng lượng thành công. Năng lượng hiện tại: {new_energy}")
                else:
                    print("❌ Không thể kích hoạt Recharge Booster: Dữ liệu không đầy đủ hoặc không có.")
            else:
                print(f"❌ Gặp sự cố với mã trạng thái {response.status}, thử lại...")
                return None 

async def activate_booster(index, headers, proxy):
    proxy = load_proxy()  
    if not proxy:
        print("Không tìm thấy proxy hợp lệ.")
        return None, None
    result = await fetch(index + 1, proxy)
    if not result:
        return None

    access_token, _ = result

    url = "https://api-gw-tg.memefi.club/graphql"
    print("\r🚀 Kích hoạt Turbo Boost... ", end="", flush=True)

    headers = headers_set.copy() 
    headers['Authorization'] = f'Bearer {access_token}'

    recharge_booster_payload = {
        "operationName": "telegramGameActivateBooster",
        "variables": {"boosterType": "Turbo"},
        "query": QUERY_BOOSTER
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=recharge_booster_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                current_health = response_data['data']['telegramGameActivateBooster']['currentBoss']['currentHealth']
                if current_health == 0:
                    print("\nBoss đã bị hạ gục, chuyển boss tiếp theo...")
                    await set_next_boss(index, headers, proxy)
                else:
                    total_hit = 3000
                    tap_payload = {
                        "operationName": "MutationGameProcessTapsBatch",
                        "variables": {
                            "payload": {
                                "nonce": generate_random_nonce(),
                                "tapsCount": total_hit
                            }
                        },
                        "query": MUTATION_GAME_PROCESS_TAPS_BATCH
                    }
                    for _ in range(25):
                        tap_result = await submit_taps(index, tap_payload, proxy)
                        if tap_result is not None:
                            if 'data' in tap_result and 'telegramGameProcessTapsBatch' in tap_result['data']:
                                tap_data = tap_result['data']['telegramGameProcessTapsBatch']
                                if tap_data['currentBoss']['currentHealth'] == 0:
                                    print("\nBoss đã bị hạ gục, chuyển boss tiếp theo...")
                                    await set_next_boss(index, headers, proxy)
                                    print(f"\rĐang tap memefi: {tap_data['coinsAmount']}, Boss ⚔️: {tap_data['currentBoss']['currentHealth']} - {tap_data['currentBoss']['maxHealth']}    ")
                        else:
                            print(f"❌ Gặp sự cố với mã trạng thái {tap_result}, thử lại...")
                            print(f"URL: {url}")
                            print(f"Headers: {headers}")
                            response_text = await response.text()
                            print(f"Response: {response_text}")
                            
            else:
                print(f"❌ Gặp sự cố với mã trạng thái {response.status}, thử lại...")
                print(f"URL: {url}")
                print(f"Headers: {headers}")
                print(f"Payload: {json_payload}")

                response_text = await response.text()
                print(f"Response: {response_text}")
                return None 

async def submit_taps(index, json_payload, proxy):
    try:
        proxy = load_proxy()  
        if not proxy:
            print("Không tìm thấy proxy hợp lệ.")
            return None, None
        result = await fetch(index + 1, proxy)
        if not result:
            return None

        access_token, _ = result

        headers = headers_set.copy()
        headers['Authorization'] = f'Bearer {access_token}'

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_payload, proxy=proxy) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data
                else:
                    print(f"❌ Thất bại với trạng thái {response}, thử lại...")
                    return None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        print(f"Lỗi kết nối máy chủ: {e}")
        return None 


async def set_next_boss(index, headers, proxy):
    proxy = load_proxy() 
    if not proxy:
        print("Không tìm thấy proxy hợp lệ.")
        return None, None
    result = await fetch(index + 1, proxy)
    if not result:
        return None

    access_token, _ = result

    url = "https://api-gw-tg.memefi.club/graphql"

    headers = headers_set.copy()
    headers['Authorization'] = f'Bearer {access_token}'

    json_payload = {
        "operationName": "telegramGameSetNextBoss",
        "variables": {},
        "query": QUERY_NEXT_BOSS
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                if response_data and 'data' in response_data:
                    print("Boss tiếp theo đã được đặt thành công!")
                    return response_data
                else:
                    print("❌ Không thể đặt Boss tiếp theo: Dữ liệu không đầy đủ hoặc không có.")
                    return None
            else:
                print(f"❌ Gặp sự cố với mã trạng thái {response.status}, thử lại...")
                print(f"URL: {url}")
                print(f"Headers: {headers}")
                print(f"Payload: {json_payload}")

                response_text = await response.text()
                print(f"Response: {response_text}")
                return None



async def check_stat(index, headers, proxy):
    proxy = load_proxy()  
    if not proxy:
        print("Không tìm thấy proxy hợp lệ.")
        return
    result = await fetch(index + 1, proxy)
    if not result:
        return None

    access_token, _ = result

    url = "https://api-gw-tg.memefi.club/graphql"

    headers = headers_set.copy() 
    headers['Authorization'] = f'Bearer {access_token}'
    
    json_payload = {
        "operationName": "QUERY_GAME_CONFIG",
        "variables": {},
        "query": QUERY_GAME_CONFIG
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_payload, proxy=proxy) as response:
            if response.status == 200:
                response_data = await response.json()
                if 'errors' in response_data:
                    return None
                else:
                    user_data = response_data['data']['telegramGameGetConfig']
                    return user_data
            else:
                print(response)
                print(f"❌ Lỗi với trạng thái {response.status}, thử lại...")
                return None
async def main():
    print("Bắt đầu Memefi bot...")
    print("Kiểm tra proxy...", end="", flush=True)

    proxy = load_proxy()
    if not proxy:
        print("Không tìm thấy proxy hợp lệ.")
        return

    print("\nProxy hợp lệ. Lấy danh sách tài khoản...")
    
    while True:

        with open('query_id.txt', 'r') as file:
            account_lines = file.readlines()
            
            accounts = []


            for index, line in enumerate(account_lines):
                result, proxy = await check_user(index, proxy)
                if result is not None:
                    first_name = result.get('firstName', 'Unknown')
                    last_name = result.get('lastName', 'Unknown')
                    accounts.append((index, result, first_name, last_name, proxy))
                else:
                    print(f"❌ Tài khoản {index + 1}: Token không hợp lệ hoặc có lỗi xảy ra")

            print("\rDanh sách tài khoản:", flush=True)
            for index, _, first_name, last_name, proxy in accounts:
                print(f"✅ [ Tài khoản {first_name} {last_name} ] | Proxy hoạt động.")

            for index, result, first_name, last_name, proxy in accounts:
                ip_changed = await change_ip()
                if not ip_changed:
                    print(f"Không thể đổi IP cho tài khoản thứ {index + 1}. Tiếp tục với IP hiện tại.")
                else:
                    print("Đổi IP thành công, chờ 10 giây để kiểm tra địa chỉ IP mới:")
                await asyncio.sleep(10)
                await check_ip_proxy(proxy)
            
                print("Chờ 120 giây trước khi tiếp tục...")
                await asyncio.sleep(120)
                headers = {'Authorization': f'Bearer {result}'}
                should_continue_to_next_account = False
                stat_result = await check_stat(index, headers, proxy)

                if stat_result is not None:
                    user_data = stat_result
                    output = (
                        f"[ Tài khoản {index + 1} - {first_name} {last_name} ]\n"
                        f"Balance 💎 {user_data.get('coinsAmount', 'Unknown')} Năng lượng : {user_data.get('currentEnergy', 'Unknown')} / {user_data.get('maxEnergy', 'Unknown')}\n"
                        f"Boss LV {user_data['currentBoss'].get('level', 'Unknown')} ❤️  {user_data['currentBoss'].get('currentHealth', 'Unknown')} - {user_data['currentBoss'].get('maxHealth', 'Unknown')}\n"
                        f"Turbo {user_data['freeBoosts'].get('currentTurboAmount', 'Unknown')} Recharge {user_data['freeBoosts'].get('currentRefillEnergyAmount', 'Unknown')}\n"
                    )
                else:
                    print(f"⚠️ Cảnh báo: Không thể truy xuất dữ liệu người dùng cho tài khoản {index}. Chuyển sang tài khoản tiếp theo.")
                    continue
                print(output, end="", flush=True)
                if 'currentBoss' in user_data:
                    lv_boss = user_data['currentBoss']['level']
                    mau_boss = user_data['currentBoss']['currentHealth']
                    if lv_boss == 11 and mau_boss == 0:
                        print(f"\n=================== {first_name} {last_name} KẾT THÚC ====================")
                        should_continue_to_next_account = True
                    if mau_boss == 0:
                        print("\nBoss đã bị hạ gục, chuyển boss tiếp theo...", flush=True)
                        await set_next_boss(index, headers, proxy)
                print("\rBắt đầu tap\n", end="", flush=True)
            

                energy_now = user_data['currentEnergy']
                recharge_available = user_data['freeBoosts']['currentRefillEnergyAmount']
                if not should_continue_to_next_account:
                    while energy_now > 500 or recharge_available > 0:
                        total_tap = random.randint(100, 200)
                        tap_payload = {
                            "operationName": "MutationGameProcessTapsBatch",
                            "variables": {
                                "payload": {
                                    "nonce": generate_random_nonce(),
                                    "tapsCount": total_tap
                                }
                            },
                            "query": MUTATION_GAME_PROCESS_TAPS_BATCH
                        }

                        tap_result = await submit_taps(index, tap_payload, proxy)
                        if tap_result is not None:
                            user_data = await check_stat(index, headers, proxy)
                            energy_now = user_data['currentEnergy']
                            recharge_available = user_data['freeBoosts']['currentRefillEnergyAmount']
                            print(f"\rĐang tap Memefi : Balance 💎 {user_data['coinsAmount']} Năng lượng : {energy_now} / {user_data['maxEnergy']}\n")
                        else:
                            print(f"❌ Lỗi với trạng thái {tap_result}, thử lại...")

                        if energy_now < 500:
                            if recharge_available > 0:
                                print("\rHết năng lượng, kích hoạt Recharge... \n", end="", flush=True)
                                await activate_energy_recharge_booster(index, headers, proxy)
                                user_data = await check_stat(index, headers, proxy)
                                energy_now = user_data['currentEnergy']
                                recharge_available = user_data['freeBoosts']['currentRefillEnergyAmount']
                            else:
                                print("Năng lượng dưới 500 và không còn Recharge, chuyển sang tài khoản tiếp theo.")
                                break

                        if user_data['freeBoosts']['currentTurboAmount'] > 0:
                            await activate_booster(index, headers, proxy)
                if should_continue_to_next_account:
                    continue
        print("=== [ TẤT CẢ TÀI KHOẢN ĐÃ ĐƯỢC XỬ LÝ ] ===")
        animate_energy_recharge(600)

def animate_energy_recharge(duration):
    frames = ["|", "/", "-", "\\"]
    end_time = time.time() + duration
    while time.time() < end_time:
        remaining_time = int(end_time - time.time())
        for frame in frames:
            print(f"\rĐang nạp lại năng lượng {frame} - Còn lại {remaining_time} giây", end="", flush=True)
            time.sleep(0.25)
    print("\rNạp năng lượng hoàn thành.\n", flush=True)

asyncio.run(main())
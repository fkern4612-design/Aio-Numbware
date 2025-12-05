import random
import string
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich.console import Console
from rich.table import Table
from rich.live import Live

# ---------------------------
# Console for rich output
# ---------------------------
console = Console()

# ---------------------------
# Global list to store drivers
# ---------------------------
drivers = []

# ---------------------------
# Random nickname generator
# ---------------------------
def generate_random_username(length=8):
    chars = string.ascii_letters + string.digits
    return 'numb' + ''.join(random.choice(chars) for _ in range(length))

# ---------------------------
# Launch headless browser
# ---------------------------
def launch_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=options)
    drivers.append(driver)
    return driver

# ---------------------------
# Wait for clickable element
# ---------------------------
def wait_for_clickable(driver, by, locator, timeout=15, retries=5):
    for attempt in range(retries):
        try:
            wait = WebDriverWait(driver, timeout, poll_frequency=0.1)
            element = wait.until(EC.element_to_be_clickable((by, locator)))
            return element
        except:
            time.sleep(0.3)
    raise Exception(f"Element {locator} not clickable after {retries} retries")

# ---------------------------
# Bot joins game
# ---------------------------
def join_bot(game_pin: str, bot_number: int, total_bots: int, progress_list: list, live):
    driver = launch_browser()
    progress_list[bot_number-1] = "[cyan]Browser launched[/cyan]"
    update_table(progress_list, live)

    try:
        driver.get("https://www.kahoot.it")

        # Enter Game PIN
        game_input = wait_for_clickable(driver, By.ID, "game-input")
        game_input.clear()
        game_input.send_keys(game_pin)
        game_input.send_keys(Keys.ENTER)
        progress_list[bot_number-1] = "[yellow]Entered Game PIN[/yellow]"
        update_table(progress_list, live)

        # Click Join
        join_button = wait_for_clickable(driver, By.CSS_SELECTOR, "main div form button")
        driver.execute_script("arguments[0].click();", join_button)
        progress_list[bot_number-1] = "[yellow]Clicked Join button[/yellow]"
        update_table(progress_list, live)

        # Enter nickname
        nickname_input = wait_for_clickable(driver, By.CSS_SELECTOR, "#nickname")
        nickname = generate_random_username()
        nickname_input.clear()
        nickname_input.send_keys(nickname)
        nickname_input.send_keys(Keys.ENTER)
        progress_list[bot_number-1] = f"[green]Joined as {nickname}[/green]"
        update_table(progress_list, live)

        # Keep running
        progress_list[bot_number-1] = "[green]Running in background[/green]"
        update_table(progress_list, live)
        while True:
            time.sleep(10)

    except Exception as e:
        progress_list[bot_number-1] = f"[red]Error: {e}[/red]"
        update_table(progress_list, live)
        while True:
            time.sleep(10)

# ---------------------------
# Update table
# ---------------------------
def update_table(progress_list, live):
    table = Table(title="Kahoot Bots Status")
    table.add_column("Bot", justify="center")
    table.add_column("Status", justify="left")
    for i, status in enumerate(progress_list, start=1):
        table.add_row(f"{i}", status)
    live.update(table)

# ---------------------------
# Thread wrapper
# ---------------------------
def launch_bot_thread(game_pin, bot_number, total_bots, progress_list, live):
    join_bot(game_pin, bot_number, total_bots, progress_list, live)

# ---------------------------
# Main
# ---------------------------
def main():
    banner = r"""
  _   _                 _                           
 | \ | |               | |                          
 |  \| |_   _ _ __ ___ | |____      ____ _ _ __ ___ 
 | . ` | | | | '_ ` _ \| '_ \ \ /\ / / _` | '__/ _ \
 | |\  | |_| | | | | | | |_) \ V  V / (_| | | |  __/
 |_| \_|\__,_|_| |_| |_|_.__/ \_/\_/ \__,_|_|  \___|

                      [bold green]Numbware Kahoot AIO[/bold green]
"""
    console.print(banner)
    game_pin = console.input("Enter Kahoot PIN: ")
    num_bots = int(console.input("Enter number of bots to join: "))

    progress_list = ["[grey]Waiting...[/grey]"] * num_bots

    threads = []
    with Live(refresh_per_second=4) as live:
        for i in range(1, num_bots + 1):
            t = threading.Thread(target=launch_bot_thread, args=(game_pin, i, num_bots, progress_list, live))
            t.start()
            threads.append(t)
            time.sleep(0.05)  # stagger to prevent Chrome conflicts

        for t in threads:
            t.join()

if __name__ == "__main__":
    main()

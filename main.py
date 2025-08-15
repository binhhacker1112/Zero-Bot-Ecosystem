import discord
from discord.ext import commands, tasks
import random
import json
import os
from datetime import datetime, timedelta
import dotenv 
import time
import csv
from server_logger import get_logger

# --- Config ---
dotenv.load_dotenv()
TOKEN = os.getenv("BOT_DISCORD_TOKEN")  # Thay bằng token thật khi chạy
PREFIXES = ['!zero ', '!z ']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'users.json')
FOXCOIN_PRICE = os.path.join(BASE_DIR, 'foxcoin_price.csv')
MAX_FOXCOIN = 21000000000
DAILY_AMOUNT = 500
PETS_PRICE = os.path.join(BASE_DIR, 'pets_price.json')

# --- Helper Functions ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {'balance': 1000, 'last_daily': None, 'foxcoin': 0, 'pets': []}
        save_data(data)
    return data[str(user_id)]

def update_user_data(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

def save_foxcoin_price(price):
    with open(FOXCOIN_PRICE, 'a', newline='') as f:
        writer = csv.writer(f)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        writer.writerow([timestamp, price])

def get_foxcoin_price():
    with open(FOXCOIN_PRICE, 'r', newline='') as f:
        rows = list(csv.reader(f))
        if len(rows) == 1:
            return 10.0
        row_now = rows[-1]
        return float(row_now[1])
    
def get_total_supply():
    data = load_data()
    return sum(user['foxcoin'] for user in data.values())

def get_pet_price(pet_name):
    if not os.path.exists(PETS_PRICE):
        return {}
    with open(PETS_PRICE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get(pet_name)

def get_pet_list():
    if not os.path.exists(PETS_PRICE):
        return {}
    with open(PETS_PRICE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.keys()

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or(*PREFIXES), intents=intents)
bot.remove_command('help')

# --- Key Words ---

balance_commands = ('balance', 'bl', 'money', 'cash', 'sodu', 'tien')
daily_commands = ('daily', 'dl', 'dail', 'dai', 'diemdanh')
coin_flip_commands = ('coinflip', 'cf')
blackjack_commands = ('blackjack', 'bj', 'xidach')
love_commands = ('love', 'couple', 'ghepdoi', 'otp', 'ship', 'daythuyen')
foxcoin_commands = ('foxcoin', 'fxc')
leaderboard_commands = ('leaderboard', 'ldb', 'bxh')
spin_commands = ('spin', 's', 'sp')
shop_commands = ('shop', 'store', 'cuahang')
work_commands = ('work', 'lamviec', 'lv')

# --- Economy Commands ---
@bot.command(name='balance', aliases = balance_commands[1:])
async def balance(ctx):
    user_data = get_user_data(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention} Số dư hiện tại: **{user_data['balance']:,.2f}**")

@bot.command(name='daily', aliases = daily_commands[1:])
async def daily(ctx):
    user_data = get_user_data(ctx.author.id)
    now = datetime.utcnow()
    last_daily = user_data.get('last_daily')
    if last_daily:
        last_daily = datetime.fromisoformat(last_daily)
        if now - last_daily < timedelta(hours=24):
            remain = timedelta(hours=24) - (now - last_daily)
            await ctx.send(f"⏳ Bạn đã nhận daily rồi. Thử lại sau {remain.seconds//3600}h{(remain.seconds//60)%60}p.")
            return
    user_data['balance'] += DAILY_AMOUNT
    user_data['last_daily'] = now.isoformat()
    update_user_data(ctx.author.id, user_data)
    await ctx.send(f"🎁 {ctx.author.mention} nhận {DAILY_AMOUNT} xu mỗi ngày! Số dư mới: **{user_data['balance']:.2f}**")

# --- Coinflip Command ---
@bot.command(name='coinflip', aliases = coin_flip_commands[1:])
async def coinflip(ctx, choice: str = None, amount: str = None):
    if choice not in ['heads', 'tails'] or amount is None:
        await ctx.send('Cú pháp: `!zero coinflip heads/tails <số tiền>`')
        return
    user_data = get_user_data(ctx.author.id)
    if amount.isdigit():
        amount = int(amount)
    else:
        if amount not in ['all']:
            await ctx.send('Cú pháp: `!zero coinflip heads/tails <số tiền>`')
            return
        amount = user_data['balance']
    if amount <= 0 or amount > user_data['balance']:
        await ctx.send('Số tiền cược không hợp lệ hoặc vượt quá số dư!')
        return
    result = random.choice(['heads', 'tails'])
    win = (choice == result)
    if win:
        user_data['balance'] += amount
        msg = f"🎉 {ctx.author.mention} thắng! Kết quả: **{result}**. Nhận {amount:,.2f} xu."
    else:
        user_data['balance'] -= amount
        msg = f"😢 {ctx.author.mention} thua! Kết quả: **{result}**. Mất {amount:,.2f} xu."
    update_user_data(ctx.author.id, user_data)
    await ctx.send(msg + f" Số dư: **{user_data['balance']:,.2f}**")

# --- Blackjack Game ---
SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
CARD_VALUES = {str(i): i for i in range(2, 11)}
CARD_VALUES.update({'J': 10, 'Q': 10, 'K': 10, 'A': 11})

def draw_card(deck):
    return deck.pop(random.randint(0, len(deck)-1))

def hand_value(hand):
    value = sum(CARD_VALUES[card[0]] for card in hand)
    # Adjust for Aces
    aces = sum(1 for card in hand if card[0] == 'A')
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

active_blackjack = {}

@bot.command(name='blackjack', aliases = blackjack_commands[1:])
async def blackjack(ctx, amount: str = None):
    if amount.isdigit():
        amount = int(amount)
        if amount is None or amount <= 0:
            await ctx.send('Cú pháp: `!zero blackjack <số tiền>`')
            return
        user_data = get_user_data(ctx.author.id)
        if amount > user_data['balance']:
            await ctx.send('Số dư không đủ để chơi!')
            return
        if ctx.author.id in active_blackjack:
            await ctx.send('Bạn đang có ván blackjack chưa kết thúc!')
            return
    else:
        if amount == 'all':
            user_data = get_user_data(ctx.author.id)
            if user_data['balance'] == 0:
                await ctx.send('Số dư không đủ để chơi!')
                return
            amount = user_data['balance']
        else:
            await ctx.send('Số tiền bạn nhập không hợp lệ!')
            return
    # Setup game
    deck = [(rank, suit) for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    player = [draw_card(deck), draw_card(deck)]
    dealer = [draw_card(deck), draw_card(deck)]
    active_blackjack[ctx.author.id] = {
        'deck': deck,
        'player': player,
        'dealer': dealer,
        'bet': amount
    }
    await ctx.send(f"Bài của bạn: {format_hand(player)} (Tổng: {hand_value(player)})\nBài dealer: {format_hand([dealer[0]])} và [ẩn]\nGõ `hit` để rút, `stand` để dừng.")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['hit', 'stand']

    while True:
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
        except:
            del active_blackjack[ctx.author.id]
            await ctx.send('⏰ Hết thời gian! Ván bài bị hủy.')
            return
        if msg.content.lower() == 'hit':
            player.append(draw_card(deck))
            await ctx.send(f"Bạn rút: {format_hand([player[-1]])}. Bài: {format_hand(player)} (Tổng: {hand_value(player)})")
            if hand_value(player) > 21:
                user_data['balance'] -= amount
                update_user_data(ctx.author.id, user_data)
                del active_blackjack[ctx.author.id]
                await ctx.send(f'💥 Quá 21! Bạn thua **{amount:,.2f}** xu. Số dư: **{user_data["balance"]:,.2f}**')
                return
        else:
            break
    # Dealer turn
    while hand_value(dealer) < 17:
        dealer.append(draw_card(deck))
    await ctx.send(f"Bài dealer: {format_hand(dealer)} (Tổng: {hand_value(dealer)})")
    player_val = hand_value(player)
    dealer_val = hand_value(dealer)
    if dealer_val > 21 or player_val > dealer_val:
        user_data['balance'] += amount
        result = f'🎉 Bạn thắng **{amount:,.2f}** xu!'
    elif player_val == dealer_val:
        result = '🤝 Hòa! Không mất tiền.'
    else:
        user_data['balance'] -= amount
        result = f'😢 Bạn thua **{amount:,.2f}** xu.'
    update_user_data(ctx.author.id, user_data)
    del active_blackjack[ctx.author.id]
    await ctx.send(f'{result} Số dư: **{user_data["balance"]:,.2f}**')

def format_hand(hand):
    return ', '.join([f'{r}{s}' for r, s in hand])
@bot.command(name='help')
async def help(ctx):
    embed = discord.Embed(
        title="📘 Hướng dẫn sử dụng BOT - Zero Bot Beta 2.3",
        description="Danh sách đầy đủ các lệnh",
        color=discord.Color.blue()
    )
    
    categories = {
        "💰 Kinh tế": [
            "`!z daily` - Nhận quà hàng ngày",
            "`!z work` - Làm việc kiếm tiền (30p/lần)",
            "`!z give @user <amount>` - Tặng tiền",
            "`!z rob @user` - Cướp tiền (1h/lần)"
        ],
        "🎮 Mini Games": [
            "`!z blackjack <amount>` - Chơi xì dách",
            "`!z coinflip <heads/tails> <amount>` - Tung đồng xu",
            "`!z spin <amount>` - Quay slot",
            "`!z taixiu <tai/xiu> <amount>` - Cá cược tài xỉu"
        ],
        "🛒 Cửa hàng": [
            "`!z shop` - Xem cửa hàng",
            "`!z shop buy <item>` - Mua vật phẩm",
            "`!z inventory` - Xem kho đồ"
        ],
        "📊 Khác": [
            "`!z foxcoin <check/buy/sell>` - Giao dịch foxcoin",
            "`!z leaderboard` - Bảng xếp hạng",
            "`!z love @user1 @user2` - Xem độ hợp nhau"
        ]
    }
    
    for category, commands in categories.items():
        embed.add_field(name=category, value="\n".join(commands), inline=False)
    
    embed.set_footer(text=f"Prefix: {', '.join(PREFIXES)} | Zero Bot Beta 2.2")
    await ctx.send(embed=embed)

@bot.command(name='love', aliases=love_commands[1:])
async def love(ctx):
    mentions = ctx.message.mentions
    if len(mentions) != 2:
        await ctx.send("Vui lòng nhập đúng cú pháp `!z love <Người dùng 1> <Người dùng 2>`")
        return
    
    user1, user2 = mentions[0], mentions[1]
    user_id1, user_id2 = user1.id, user2.id
    def tong_chu_so(n):
        j = n // 10
        k = n % 10
        if j + k > 9:
            return tong_chu_so(j+k)
        return j+k
    s1, s2 = tong_chu_so(user_id1), tong_chu_so(user_id2)
    hop_nhau = (int((s1*s2)**0.5) + random.randint(0, 100)) % 100
    await ctx.send(f"Tỷ lệ hợp nhau của 2 bạn là {hop_nhau}%")
    if hop_nhau == 100:
        await ctx.send(
            "💍 **CẦN ĐỂ GẤP!!!!!** 💍\n"
            "Vì 2 bạn là định mệnh là có thật! 💘 Hai bạn là cặp đôi hoàn hảo từ tên đến trái tim! 💍💖 Chúc mừng vì đã tìm thấy nửa kia của mình!"
            )
    elif 99 >= hop_nhau >= 90:
        await ctx.send("Mình nghĩ 2 bạn nên về chung 1 nhà với nhau! 🏡💑")
    elif 89 >= hop_nhau >= 80:
        await ctx.send("Một tình yêu đáng ngưỡng mộ! 💖")
    elif 79 >= hop_nhau >= 70:
        await ctx.send("Rất hợp nhau đấy! Thử tìm hiểu thêm xem sao! 😊")
    elif 69 >= hop_nhau >= 50:
        await ctx.send("Cũng tạm ổn, nhưng vẫn cần cố gắng! 🤝")
    elif 49 >= hop_nhau >= 30:
        await ctx.send("Hmm... Có lẽ chỉ nên làm bạn. 😅")
    elif 29 >= hop_nhau >= 10:
        await ctx.send("Khó đấy... chắc không cùng tần số. 😬")
    elif 9 >= hop_nhau >= 1:
        await ctx.send("💔 Oan gia trái số luôn rồi!")
    else:
        await ctx.send("Là do giá trị không hợp lệ hay... **không hợp nhau**? 🤖")

@bot.command(name='foxcoin', aliases=foxcoin_commands[1:])
async def foxcoin(ctx, choice: str = None, number: str = None):
    msg_khong_hop_le = 'Hãy chọn 1 trong 3 lựa chọn dưới đây:\nKiểm tra giá và số lượng foxcoin đang sở hữu. `!z foxcoin check`\nMua foxcoin. `!z foxcoin buy <số lượng>`\nBán foxcoin. `!z foxcoin sell <số lượng>`'
    if choice not in ['check', 'buy', 'sell']:
        await ctx.send(msg_khong_hop_le)
        return
    user_data = get_user_data(ctx.author.id)
    foxcoin_price = get_foxcoin_price()
    if choice == 'check':
        if number is not None:
            await ctx.send(msg_khong_hop_le)
            return
        so_coin = user_data['foxcoin']
        await ctx.send(
            f'Bạn đang có **{so_coin:,.2f}** foxcoin.\n'
            f'Nguồn cung foxcoin trên thị trường hiện tại là **{get_total_supply():,.2f}/{MAX_FOXCOIN:,.2f}**\n'
            f'Giá 1 foxcoin hiện tại là **{get_foxcoin_price()}**\n'
            f'Tổng giá trị số foxcoin bạn đang sở hữu là **{(get_foxcoin_price() * so_coin):,.2f}**'
            )
        return
    if number.isdigit():
        number = int(number)
    else:
        if number == 'all':
            if choice in ['buy']:
                if (user_data['balance'] / foxcoin_price) + get_total_supply() <= MAX_FOXCOIN:
                    number = user_data['balance'] / foxcoin_price
                else:
                    number = MAX_FOXCOIN - get_total_supply()
            elif choice in ['sell']:
                number = user_data['foxcoin']
        else:
            await ctx.send('Số tiền bạn nhập không hợp lệ!')
            return        
    if number is None:
        await ctx.send(msg_khong_hop_le)
        return
    if choice == 'buy':
        if number <= 0 or number*foxcoin_price > user_data['balance']:
            await ctx.send('Số foxcoin không hợp lệ hoặc vượt quá số dư!')
            return
        if number + get_total_supply() > MAX_FOXCOIN:
            await ctx.send('Số lượng foxcoin có sẵn trên thị trường hiện không đủ!')
            return
        if get_total_supply() == MAX_FOXCOIN:
            await ctx.send('Số lượng foxcoin đã đạt đến giới hạn!')
        user_data['balance'] -= float(format(number*foxcoin_price, '.2f'))
        user_data['foxcoin'] += number
        msg = 'mua'
    elif choice == 'sell':
        if number <= 0 or number > user_data['foxcoin']:
            await ctx.send('Số foxcoin không hợp lệ hoặc vượt quá số lượng bạn đang có!')
            return
        user_data['balance'] += float(format(number*foxcoin_price, '.2f'))
        user_data['foxcoin'] -= number
        msg = 'bán'
    update_user_data(ctx.author.id, user_data)
    await ctx.send(
        "Bạn đã " + msg + ' **' + str(format(number, '.2f')) + f"** foxcoin với tổng giá trị giao dịch là **{(number*foxcoin_price):,.2f}**.\n"
        f"Hiện tại bạn có **{user_data['foxcoin']:,.2f}** foxcoin.\n"
        f"Số dư: **{user_data['balance']:,.2f}**."
                       )
        
@tasks.loop(hours=1)
async def update_price():
    foxcoin_price = get_foxcoin_price()
    change_percent = random.choice([0.005, -0.005, 0.01, -0.01, 0.02, -0.02, 0.03, -0.03])
    foxcoin_price *= (1 + change_percent)
    save_foxcoin_price(round(foxcoin_price, 2))

@bot.command(name='leaderboard', aliases=leaderboard_commands[1:])
async def leaderboard(ctx):
    def bubble_sort(arr):
        for i in range(len(arr)):
            for j in range(len(arr)-i-1):
                if arr[j][1] < arr[j+1][1]:
                    arr[j], arr[j+1] = arr[j+1], arr[j]
        return arr[:10]
    
    data = load_data()
    leaderboard_list = []
    for user_id, user_data in data.items():
        leaderboard_list.append((user_id, user_data['balance'] + user_data['foxcoin']*get_foxcoin_price()))
    leaderboard_list = bubble_sort(leaderboard_list)
    embed = discord.Embed(title="🏆 Bảng xếp hạng tài sản 🏆", color=discord.Color.gold())
    for rank, (user_id, total_value) in enumerate(leaderboard_list, start=1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(
            name = f"{rank}. {user.name}",
            value = f"Tổng tài sản: {total_value:.2f}",
            inline = False
        )
    await ctx.send(embed=embed)

@bot.command(name='taisan')
async def taisan(ctx):
    user_data = get_user_data(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention} Tài sản của bạn gồm có:\n- Số dư: **{user_data['balance']:,.2f}**\n- Foxcoin: **{user_data['foxcoin']:,.2f}** foxcoin, trị giá khoảng **{user_data['foxcoin']*get_foxcoin_price():,.2f}** *({get_foxcoin_price():,.2f}/foxcoin)*\nTổng tài sản của bạn là: **{user_data['balance']+user_data['foxcoin']*get_foxcoin_price():,.2f}**")

@bot.command(name='spin', aliases=spin_commands[1:])
async def spin(ctx, amount: str = None):
    if amount is None:
        await ctx.send('Hãy nhập đúng cú pháp! `!z spin <số tiền cược>`')
        return
    user_data = get_user_data(ctx.author.id)
    if amount.isdigit():
        amount = int(amount)
        if amount <= 0 or amount > user_data['balance']:
            await ctx.send('Số tiền cược không hợp lệ hoặc số dư không đủ!')
            return
    else:
        if amount not in ['all']:
            await ctx.send('Hãy nhập đúng cú pháp! `!z spin <số tiền cược>`')
            return
        amount = user_data['balance']
    slots = ['🍕','🍔','🍟','🌭','🍿','🍖','🍗','🥩','🍠','🍘','🍤','🍉']
    result = random.choices(slots, k=3)
    if result[0] == result[1] == result[2]:
        msg = f"🎉 {ctx.author.mention} thắng! Nhận **{amount:,.2f}** xu.\n"
        user_data['balance'] += amount
    else:
        msg = f"😢 {ctx.author.mention} thua! Mất **{amount:,.2f}** xu.\n"
        user_data['balance'] -= amount
    update_user_data(ctx.author.id, user_data)
    await ctx.send('Đang quay số... Vui lòng đợi!\nKết quả: **' + ' | '.join(result) + '**\n' + msg + 'Số dư: **' + format(user_data['balance'], ',.2f') + '**')

@bot.command(name='taixiu')
async def taixiu(ctx, choice: str = None, amount: str = None):
    if choice not in ['tai', 'xiu'] or amount is None:
        await ctx.send('Cú pháp: `!z taixiu tai/xiu <số tiền>`')
        return
    if amount is None:
        await ctx.send('Cú pháp: `!z taixiu tai/xiu <số tiền>`')
        return
    user_data = get_user_data(ctx.author.id)
    if amount.isdigit():
        amount = int(amount)
    else:
        if amount not in ['all']:
            await ctx.send('Cú pháp: `!z taixiu tai/xiu <số tiền>`')
            return
        amount = user_data['balance']
    if amount <= 0 or amount > user_data['balance']:
        await ctx.send('Số tiền cược không hợp lệ hoặc vượt quá số dư!')
        return
    result1 = random.randint(1, 6)
    result2 = random.randint(1, 6)
    result3 = random.randint(1, 6)
    total_result = result1 + result2 + result3
    if 10 >= total_result >= 4:
        if choice in ['xiu']:
            user_data['balance'] += amount
            msg = f"🎉 Chúc mừng {ctx.author.mention} thắng!\nTổng điểm: **{result1} + {result2} + {result3} = {total_result}**.\nKết quả: **XỈU**.\nNhận **{amount:,.2f}** xu."
        else:
            user_data['balance'] -= amount
            msg = f"😢 Rất tiếc! {ctx.author.mention} thua!\nTổng điểm: **{result1} + {result2} + {result3} = {total_result}**.\nKết quả: **XỈU**.\nMất **{amount:,.2f}** xu."
    elif 17 >= total_result >= 11:
        if choice in ['tai']:
            user_data['balance'] += amount
            msg = f"🎉 Chúc mừng {ctx.author.mention} thắng!\nTổng điểm: **{result1} + {result2} + {result3} = {total_result}**.\nKết quả: **TÀI**.\nNhận **{amount:,.2f}** xu."
        else:
            user_data['balance'] -= amount
            msg = f"😢 Rất tiếc! {ctx.author.mention} thua!\nTổng điểm: **{result1} + {result2} + {result3} = {total_result}**.\nKết quả: **TÀI**.\nMất **{amount:,.2f}** xu."
    else:
        msg = f"Tổng điểm: **{result1} + {result2} + {result3} = {total_result}**.\nKết quả: **NHÀ CÁI ĂN**.\nKhông bị mất xu."

    update_user_data(ctx.author.id, user_data)
    await ctx.send(msg + f" Số dư: **{user_data['balance']:,.2f}**")

@bot.command(name='pets')
async def pets(ctx, choice: str = None, pets_name: str = None):
    if choice not in ['buy', 'sell', 'feed', 'give'] or pets_name not in get_pet_list():
        await ctx.send("Hãy nhập đúng cú pháp!\n`!z pets buy/sell <tên pet>`\n`!z pets feed <tên pet>`\n`!z pets give <tên pet><người dùng>`")
        return
    user_data = get_user_data(ctx.author.id)
    if not user_data:
        await ctx.send("❌ Không thể tải dữ liệu người dùng.")
        return

    if choice == 'give':
        if not ctx.message.mentions:
            await ctx.send("❌ Bạn cần tag người nhận!")
            return
        recipient = ctx.message.mentions[0]
        if recipient.id == ctx.author.id:
            await ctx.send("❌ Bạn không thể tặng pet cho chính mình!")
            return

        recipient_data = get_user_data(recipient.id)
        if not recipient_data:
            await ctx.send("❌ Người nhận không hợp lệ hoặc chưa có dữ liệu!")
            return
        if pets_name not in user_data['pets']:
            await ctx.send("❌ Bạn không sở hữu pet này!")
            return

        user_data['pets'].remove(pets_name)
        recipient_data.setdefault('pets', []).append(pets_name)
        update_user_data(ctx.author.id, user_data)
        update_user_data(recipient.id, recipient_data)
        await ctx.send(f"🎁 {ctx.author.mention} đã tặng pet **{pets_name}** cho {recipient.mention}!")
        return
    elif choice == 'buy':
        if user_data['balance'] < get_pet_price(pets_name):
            await ctx.send("❌ Số dư không đủ để mua pet này!")
            return
        user_data['balance'] -= get_pet_price(pets_name)
        user_data.setdefault('pets', []).append(pets_name)
        msg = f"🎉 {ctx.author.mention} đã mua pet **{pets_name}** với giá **{get_pet_price(pets_name):,.2f}** xu!"
    elif choice == 'sell':
        if pets_name not in user_data.get('pets', []):
            await ctx.send("❌ Bạn không sở hữu pet này!")
            return
        user_data['pets'].remove(pets_name)
        user_data['balance'] += get_pet_price(pets_name) * 0.8
        msg = f"💰 {ctx.author.mention} đã bán pet **{pets_name}** và nhận được **{get_pet_price(pets_name) * 0.8:,.2f}** xu!"
    elif choice == 'feed':
        if pets_name not in user_data.get('pets', []):
            await ctx.send("❌ Bạn không sở hữu pet này!")
            return
        feed_cost = 50
        if user_data['balance'] < feed_cost:
            await ctx.send("❌ Số dư không đủ để cho ăn pet này!")
            return
        user_data['balance'] -= feed_cost
        msg = f"🍖 {ctx.author.mention} đã cho pet **{pets_name}** ăn và mất **{feed_cost:,.2f}** xu!"
    await ctx.send(msg + f' Số dư hiện tại: **{user_data["balance"]:,.2f}** xu.\nDanh sách pet của bạn: **' + ', '.join(user_data.get('pets', [])) + "**")
    update_user_data(ctx.author.id, user_data)

@bot.command(name='info')
async def info(ctx):
    await ctx.send("""🤖 Giới thiệu về Bot

Chào bạn! Mình là **Zero Bot Beta 2.2**, một bot Discord thân thiện được tạo ra để giúp server của bạn trở nên vui vẻ và thú vị hơn!

📚 Dùng lệnh `!z help` để xem tất cả các lệnh mà mình hỗ trợ.
🛠 Luôn được cập nhật và cải tiến để mang đến trải nghiệm tốt nhất!

📬 Có góp ý hay cần hỗ trợ? Liên hệ:
            -Discord: https://discord.gg/5UmC7yXVye
            -Email:
            -Facebook: https://www.facebook.com/profile.php?id=61578577050196""")

# --- Rob Command ---
rob_cooldowns = {}

@bot.command(name='rob', aliases=('cuop', 'trom'))
async def rob(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("Cú pháp: `!z rob @người_dùng`")
        return
    
    if member.id == ctx.author.id:
        await ctx.send("Bạn không thể tự cướp chính mình!")
        return
    
    # Cooldown check (1 hour)
    now = time.time()
    last_rob = rob_cooldowns.get(ctx.author.id, 0)
    if now - last_rob < 3600:
        remaining = 3600 - (now - last_rob)
        mins = int(remaining // 60)
        await ctx.send(f"⏳ Bạn cần chờ {mins} phút nữa trước khi cướp tiếp!")
        return
    
    robber_data = get_user_data(ctx.author.id)
    victim_data = get_user_data(member.id)
    
    # Victim must have at least 100 coins
    if victim_data['balance'] < 100:
        await ctx.send("Nạn nhân không có đủ tiền để cướp!")
        return
    
    # 40% success chance
    if random.random() < 0.4:
        # Steal 10-25% of victim's balance
        steal_percent = random.uniform(0.1, 0.25)
        amount = random.randint(100, 500)
        
        victim_data['balance'] -= amount
        robber_data['balance'] += amount
        
        update_user_data(member.id, victim_data)
        update_user_data(ctx.author.id, robber_data)
        
        rob_cooldowns[ctx.author.id] = now
        await ctx.send(
            f"💰 {ctx.author.mention} đã cướp thành công {amount:,.2f} xu từ {member.mention}!\n"
            f"Số dư hiện tại: {robber_data['balance']:,.2f} xu"
        )
    else:
        # Fine for failed robbery
        fine = min(int(robber_data['balance'] * 0.05), 5000)
        robber_data['balance'] -= fine
        update_user_data(ctx.author.id, robber_data)
        
        rob_cooldowns[ctx.author.id] = now
        await ctx.send(
            f"🚨 {ctx.author.mention} đã bị bắt khi cố cướp {member.mention}!\n"
            f"Bạn bị phạt {fine:,.2f} xu\n"
            f"Số dư hiện tại: {robber_data['balance']:,.2f} xu"
        )

# --- Give Money Command ---
@bot.command(name='give', aliases=('gift', 'tang'))
async def give(ctx, member: discord.Member = None, amount: int = None):
    if member is None or amount is None:
        await ctx.send("Cú pháp: `!z give @người_dùng <số tiền>`")
        return
    
    if member.id == ctx.author.id:
        await ctx.send("Bạn không thể tự tặng tiền cho chính mình!")
        return
    
    if amount <= 0:
        await ctx.send("Số tiền phải lớn hơn 0!")
        return
    
    sender_data = get_user_data(ctx.author.id)
    receiver_data = get_user_data(member.id)
    
    if sender_data['balance'] < amount:
        await ctx.send("Số dư không đủ để thực hiện giao dịch!")
        return
    
    # Transfer money
    sender_data['balance'] -= amount
    receiver_data['balance'] += amount
    
    update_user_data(ctx.author.id, sender_data)
    update_user_data(member.id, receiver_data)
    
    await ctx.send(
        f"🎁 {ctx.author.mention} đã tặng {amount:,.2f} xu cho {member.mention}!\n"
        f"Số dư của bạn còn: {sender_data['balance']:,.2f} xu"
    )

# --- Inventory System ---
@bot.command(name='inventory', aliases=('inv', 'tui'))
async def inventory(ctx, member: discord.Member = None):
    target = member or ctx.author
    user_data = get_user_data(target.id)
    inventory = user_data.get('inventory', {})
    
    if not inventory:
        await ctx.send(f"{'Bạn' if target == ctx.author else target.display_name} chưa có vật phẩm nào!")
        return
    
    embed = discord.Embed(
        title=f"🎒 KHO ĐỒ CỦA {target.display_name.upper()}",
        color=discord.Color.blue()
    )
    
    for item, quantity in inventory.items():
        if item in SHOP_ITEMS:
            emoji = SHOP_ITEMS[item]['emoji']
            embed.add_field(name=f"{emoji} {item.capitalize()}", value=f"Số lượng: {quantity}", inline=True)
    
    await ctx.send(embed=embed)

# --- Work System ---
@bot.command(name='work', aliases=work_commands[1:])
async def work(ctx):
    user_data = get_user_data(ctx.author.id)
    now = time.time()
    last_work = user_data.get('last_work')
    
    # 30 minutes cooldown
    if last_work and (now - last_work) < 1800:
        remaining = 1800 - (now - last_work)
        mins, secs = divmod(int(remaining), 60)
        await ctx.send(f"⏳ Bạn cần nghỉ ngơi! Thử lại sau {mins} phút {secs} giây")
        return
    
    # Earn between 100-500 coins
    earnings = random.randint(100, 500)
    user_data['balance'] += earnings
    user_data['last_work'] = now
    update_user_data(ctx.author.id, user_data)
    
    jobs = ["lập trình", "thiết kế", "nhiếp ảnh", "viết content", "dịch thuật"]
    job = random.choice(jobs)
    
    await ctx.send(
        f"💼 {ctx.author.mention} đã làm công việc **{job}** và kiếm được **{earnings}** xu!\n"
        f"Số dư hiện tại: **{user_data['balance']:,.2f}** xu"
    )

# --- Shop System ---
SHOP_ITEMS = {
    "diamond": {"price": 5000, "emoji": "💎", "description": "Vật phẩm quý hiếm"},
    "gold": {"price": 1000, "emoji": "🥇", "description": "Vàng nguyên chất"},
    "potion": {"price": 300, "emoji": "🧪", "description": "Thuốc hồi phục"},
    "key": {"price": 2000, "emoji": "🔑", "description": "Chìa khóa bí mật"}
}

@bot.command(name='shop', aliases=shop_commands[1:])
async def shop(ctx, action: str = None, item: str = None, amount: int = 1):
    if action is None:
        embed = discord.Embed(title="🛒 CỬA HÀNG VẬT PHẨM 🛒", color=discord.Color.gold())
        for item_id, details in SHOP_ITEMS.items():
            embed.add_field(
                name=f"{details['emoji']} {item_id.capitalize()} - {details['price']:,} xu",
                value=details['description'],
                inline=False
            )
        embed.set_footer(text="Sử dụng !z shop buy <tên vật phẩm> [số lượng] để mua")
        await ctx.send(embed=embed)
        return
    
    if action == "buy":
        if item is None:
            await ctx.send("Vui lòng chọn vật phẩm! Ví dụ: `!z shop buy diamond`")
            return
        
        item = item.lower()
        if item not in SHOP_ITEMS:
            await ctx.send("Vật phẩm không tồn tại trong cửa hàng!")
            return
        
        user_data = get_user_data(ctx.author.id)
        item_price = SHOP_ITEMS[item]["price"] * amount
        
        if user_data['balance'] < item_price:
            await ctx.send(f"Số dư không đủ! Bạn cần thêm {item_price - user_data['balance']:,.2f} xu")
            return
        
        # Update inventory
        inventory = user_data.get('inventory', {})
        inventory[item] = inventory.get(item, 0) + amount
        user_data['inventory'] = inventory
        user_data['balance'] -= item_price
        
        update_user_data(ctx.author.id, user_data)
        await ctx.send(
            f"🎉 {ctx.author.mention} đã mua {amount} {SHOP_ITEMS[item]['emoji']} {item} "
            f"với giá {item_price:,.2f} xu!\n"
            f"Số dư còn lại: {user_data['balance']:,.2f} xu"
        )
    
    elif action == "sell":
        # Similar implementation to buy
        pass

@bot.command(name="dish")
async def hom_nay_an_gi(ctx):
    dishes = [
    "mì", "cơm", "bún", "cây", "roi", "thịt heo", "thịt bò", "thịt bò Kobe", "đấm", 
    "phở", "cháo", "hủ tiếu", "bánh mì", "bánh cuốn",
    "gà rán", "vịt quay", "nem rán", "bánh xèo", "bánh tráng trộn",
    "trà đá", "sinh tố bơ", "chè ba màu",
    "lẩu thái", "lẩu bò", "lẩu cá", "mì cay cấp độ 7", 
    "cơm tấm", "cơm gà xối mỡ", "cơm chiên dương châu", "bún bò Huế",
    "cà ri gà", "gỏi cuốn", "bò lúc lắc", "chân gà nướng", 
    "nộm bò khô", "xúc xích nướng", "kẹo mút", "kẹo cao su",
    "cơm chan nước mắt", "gan ngỗng"]

    drinks = [ "trà sữa", "nước lọc", "cà phê sữa", "cà phê đen", "trà đào", "trà chanh", "sinh tố bơ", "sinh tố xoài", "nước cam", "nước ép dứa", "soda chanh", "coca cola", "pepsi", "sữa tươi", "sữa đậu nành", "matcha latte", "trà ô long", "nước dừa", "sâm bí đao", "nước mía"]
    
    a = random.choices([1, 2, 3], weights=[0.4, 0.4, 0.2], k=1)[0]
    if a == 1:
        await ctx.send(f"Mình nghĩ hôm nay bạn nên ăn {random.choice(dishes)}")
    elif a == 2:
        await ctx.send(f"Mình nghĩ hôm nay bạn nên uống {random.choice(drinks)} thay cơm")
    else:
        await ctx.send(f"Mình nghĩ hôm nay bạn nên nhịn đói!")

@tasks.loop(hours=24)
async def update_server_list():
    with open("server_list.txt", "w") as f:
        for guild in bot.guilds:
            f.writelines(f"Name: {guild.name}; ID: {guild.id}\n")

@bot.event
async def on_ready(): 
    update_price.start()
    update_server_list.start()

# --- Ghi Log ---

# --- Rời server ---
@bot.event
async def on_member_remove(member):
    guild = member.guild
    logger = get_logger(guild.id)
    logger.info(f"[LEAVE] {member} đã rời khỏi server.")

# --- Tham gia server ---
@bot.event
async def on_member_join(member):
    guild = member.guild
    logger = get_logger(guild.id)

    logger.info(f"[JOIN] {member} (ID: {member.id}) đã tham gia server.")

# --- Tin nhắn bị xoá ---
@bot.event
async def on_message_delete(message):
    if message.guild and not message.author.bot:
        logger = get_logger(message.guild.id)
        logger.info(f"[DELETE] {message.author} in #{message.channel}: {message.content}")

# --- Lệnh được sử dụng ---
@bot.event
async def on_command(ctx):
    guild = ctx.guild
    if guild:
        logger = get_logger(guild.id)
        logger.info(f"[COMMAND] {ctx.author} dùng lệnh: {ctx.message.content}")

# --- Chỉnh sửa tin nhắn ---
@bot.event
async def on_message_edit(before, after):
    if before.guild and not before.author.bot and before.content != after.content:
        logger = get_logger(before.guild.id)
        logger.info(f"[EDIT] {before.author} in #{before.channel}:\n\t- Trước: {before.content}\n\t- Sau: {after.content}")

# --- Ban ---
@bot.event
async def on_member_ban(guild, user):
    logger = get_logger(guild.id)
    logger.info(f"[BAN] {user} ({user.id}) đã bị ban khỏi server.")

# --- Unban ---
@bot.event
async def on_member_unban(guild, user):
    logger = get_logger(guild.id)
    logger.info(f"[UNBAN] {user} ({user.id}) đã được unban.")

# --- Role thay đổi ---
@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        logger = get_logger(before.guild.id)
        added_roles = [r.name for r in after.roles if r not in before.roles]
        removed_roles = [r.name for r in before.roles if r not in after.roles]

        if added_roles:
            logger.info(f"[ROLE ADDED] {after} được thêm role: {', '.join(added_roles)}")
        if removed_roles:
            logger.info(f"[ROLE REMOVED] {after} bị gỡ role: {', '.join(removed_roles)}")

# --- Run Bot ---
if __name__ == '__main__':
    dotenv.load_dotenv()
    bot_discord_password = os.getenv("BOT_DISCORD_PASSWORD")
    password = input('Nhập mật khẩu để khởi động bot: ')
    if password == bot_discord_password:
        for _ in range(3):
            for i in range(1, 4):
                print('Bot đang được khởi động', '.' * i, end='\r')
                time.sleep(0.5)
            print(" " * 50, end='\r')
        print('Bot đã được khởi động.')
        bot.run(TOKEN)
        print('Bot đã offline')
    else:
        print('Mật khẩu không chính xác.')
        quit()
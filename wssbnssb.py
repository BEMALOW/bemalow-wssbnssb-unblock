import aiohttp
from hoshino import R, Service, util, priv
from nonebot import *
import asyncio
import sqlite3
from datetime import datetime,timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import apscheduler

sv = Service('wssbnssb', help_='解救那些玩bot被禁言的群友吧！')

file_path='C:\\Users\\Administrator\\Desktop\\haru-bot-setup\\hoshino\\modules\\groupmaster\\blocked.db'
scheduler = AsyncIOScheduler() #创建一个实例
##文件中的s_为search_省略 sil_为silence（禁言）省略  ##为方便理解的注释

async def sil_rw(qqid,groupid,time):
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()

        last_sil_time = datetime.now()
        last_sil_time_cache = last_sil_time
        scheduled_time_end = last_sil_time + timedelta(seconds=time)
        next_day_limit = last_sil_time.replace(hour=4, minute=0, second=0, microsecond=0) + timedelta(days=1)
        today_limit = last_sil_time.replace(hour=4, minute=0, second=0, microsecond=0 )

        scheduled_time = scheduled_time_end.strftime("%Y-%m-%d %H:%M:%S")
        last_sil_time = last_sil_time.strftime("%Y-%m-%d %H:%M:%S")

        cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT, flag TEXT)')
        insert_query = "INSERT INTO blocked(qqid,groupid,禁言时间,flag) VALUES (?, ?, ?, ?)"
        data_to_insert = (qqid, groupid,last_sil_time,0)
        cs_.execute(insert_query, data_to_insert)
        sil_db.commit()

        if scheduled_time_end <= next_day_limit:
            if last_sil_time_cache <= today_limit:
                if scheduled_time_end <= today_limit:
                    await add_scheduled(last_sil_time,scheduled_time)
            else:
                await add_scheduled(last_sil_time,scheduled_time)

                
        await asyncio.sleep(1)

async def add_scheduled(s_time,time):
    scheduler.add_job(time_to_delete, 'date', run_date=time, args=(s_time,))
    if not scheduler.running:
        scheduler.start()
    await asyncio.sleep(1)

async def time_to_delete(search_time):
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        cs_.execute('CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT, flag TEXT)')
        cs_.execute("UPDATE blocked SET flag = '1' WHERE 禁言时间 = ? ;",(search_time,))
        sil_db.commit()
    await asyncio.sleep(1)

@sv.on_fullmatch('nssb','复活吧')
async def nssb_(bot,ev):
    ev_cache = ev
    s_qqid = ev.user_id
    s_groupid = ev.group_id
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        cs_.execute('CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT ,flag TEXT)')
        cs_.execute(f"SELECT * FROM blocked WHERE flag = 1 AND groupid = {s_groupid}")
        s_result1 = cs_.fetchall()
        if not s_result1:
            await wssb_check(bot,ev)
        else:          
            for result in s_result1:
                ev.group_id = result[1]
                ev.user_id= result[0]
                await util.silence(ev, 0)
            cs_.execute(f"DELETE FROM blocked WHERE flag = 1 AND groupid = {s_groupid}")
            sil_db.commit()
            await bot.send(ev_cache,f"群友正在复活。。。。。。")
            await wssb_check(bot,ev)
            await rank_rw(s_qqid)




@on_command('wssb')
async def wssb_(ev):
    s_qqid = str(ev.event['user_id'])
    with sqlite3.connect(file_path) as sil_db:

        cs_ = sil_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT ,flag TEXT)')
        cs_.execute(f"SELECT * FROM blocked WHERE qqid = {s_qqid}")
        s_result1 = cs_.fetchall()

        if not s_result1:
            await ev.finish('你没有被禁言')
        else:
            msg=''
            for result in s_result1:
                msg += f'你被禁言的群：{result[1]}，上次被禁言是：{result[2]}。'
                ev.event.group_id = result[1] 

            cs_.execute("UPDATE blocked SET flag = '1' WHERE qqid = ? ;",(s_qqid,))
            sil_db.commit()
            msg += '请等待管理员送至重生信标'
            await ev.finish(msg)


async def rank_rw(qqid):
    with sqlite3.connect(file_path) as rank_db:
        cs_ = rank_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS rank (qqid TEXT, flag TEXT)')
        cs_.execute(f"SELECT * FROM rank WHERE qqid = {qqid}")
        rank_result = cs_.fetchall()
        if not rank_result:
            insert_query = "INSERT INTO rank(qqid, flag) VALUES (?, ?)"
            data_to_insert = (qqid,1)
            cs_.execute(insert_query, data_to_insert)
            rank_db.commit()
            await asyncio.sleep(1)
        else:
            for result in rank_result:
                r_adder = int(result[1]) + 1
                insert_query = "UPDATE rank SET flag = ? WHERE qqid = ? ;"
                data_to_insert = (str(r_adder),qqid,)
                cs_.execute(insert_query, data_to_insert)
                rank_db.commit()
            await asyncio.sleep(1)


@sv.on_fullmatch('nssbr')
async def neeb_rank(bot,ev):
    mlist = await bot.get_group_member_list(group_id=ev.group_id)
    with sqlite3.connect(file_path) as rank_db:
        cs_ = rank_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS rank (qqid TEXT, flag TEXT)')  #保险
        cs_.execute('SELECT * FROM rank')
        rank_result = cs_.fetchall()
        if not rank_result:
            await asyncio.sleep(1)
        else:    
            rankcache = sorted(rank_result, key=lambda x : int(x[1]), reverse=True)
            msg='救人排行表TOP10：\n'
            for rank in rankcache[:10]:
                for m in mlist:
                    if int(rank[0])== int(m['user_id']):
                        msg += f"{m['nickname']}救人次数：{rank[1]}\n"
            await bot.send(ev,msg)



async def wssb_check(bot,ev):
    s_groupid = ev.group_id
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        cs_.execute(f"SELECT * FROM blocked WHERE flag = 0 AND groupid = {s_groupid}")
        s_result0 = cs_.fetchall()
        if not s_result0:
            await bot.send(ev,'该群现在暂时没有人被禁言！')
        else:
            mlist = await bot.get_group_member_list(group_id=ev.group_id)
            msg = '还有下列群友未变成复活旗帜：\n'
            for result in s_result0:
                for m in mlist:
                    if int(m['user_id'])==int(result[0]):
                        msg += f"{m['nickname']}\n"
            await bot.send(ev,msg)

@sv.scheduled_job('cron', hour='4')
async def wssb_autoclean():
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT ,flag TEXT)')
        cs_.execute("UPDATE blocked SET flag = '1' ")
        sil_db.commit()
    await asyncio.sleep(1)

@sv.on_notice('group_ban')
async def wssb_claen(ev):
    qqid = ev.event['user_id']
    groupid = ev.event['group_id']
    if ev.event['sub_type'] == "ban" and ev.event['user_id'] != 0:
        with sqlite3.connect(file_path) as sil_db:

            last_sil_time = datetime.now()
            last_sil_time_cache = last_sil_time
            scheduled_time_end = last_sil_time + timedelta(seconds=ev.event['duration'])
            next_day_limit = last_sil_time.replace(hour=4, minute=0, second=0, microsecond=0) + timedelta(days=1)
            today_limit = last_sil_time.replace(hour=4, minute=0, second=0, microsecond=0 )

            scheduled_time = scheduled_time_end.strftime("%Y-%m-%d %H:%M:%S")
            last_sil_time = last_sil_time.strftime("%Y-%m-%d %H:%M:%S")

            cs_ = sil_db.cursor()
            cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT, flag TEXT)')
            insert_query = "INSERT INTO blocked(qqid,groupid,禁言时间,flag) VALUES (?, ?, ?, ?)"
            data_to_insert = (qqid, groupid,last_sil_time,0)
            cs_.execute(insert_query, data_to_insert)
            sil_db.commit()

            if scheduled_time_end <= next_day_limit:
                if last_sil_time_cache <= today_limit:
                    if scheduled_time_end <= today_limit:
                        await add_scheduled(last_sil_time,scheduled_time)
                else:
                    await add_scheduled(last_sil_time,scheduled_time)

            await asyncio.sleep(1)
    else:
        s_groupid = ev.event['group_id']
        with sqlite3.connect(file_path) as sil_db:
            cs_ = sil_db.cursor()
            cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT ,flag TEXT)')
            cs_.execute(f"SELECT * FROM blocked WHERE groupid = {s_groupid}")
            s_result0 = cs_.fetchall()
            if not s_result0 and ev.event['sub_type'] == "lift_ban":
                await ev.send("该群现在暂时没有人被禁言！")
            else:
                if ev.event['sub_type'] == "ban" and ev.event['user_id'] == 0:
                    cs_.execute(f"DELETE FROM blocked WHERE groupid = {s_groupid}")
                    sil_db.commit()
                    await ev.send("大赦天下。")
                if ev.event['sub_type'] == "lift_ban" and ev.event['user_id'] != 0:
                    cs_.execute("UPDATE blocked SET flag = '1' WHERE groupid = ? ;",(s_groupid,))
                    sil_db.commit()
                    await ev.send("管理已将被禁言的群友变为复活旗帜,请输入'nssb'复活他们。")

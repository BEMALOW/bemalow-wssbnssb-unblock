import aiohttp
from hoshino import R, Service, util, priv
from nonebot import *
import asyncio
import sqlite3
import datetime

sv = Service('wssbnssb', help_='解救那些玩bot被禁言的群友吧！')

file_path='C:\\Users\\Administrator\\Desktop\\haru-bot-setup\\hoshino\\modules\\groupmaster\\blocked.db'
rank_path='C:\\Users\\Administrator\\Desktop\\haru-bot-setup\\hoshino\\modules\\groupmaster\\rank.db'

async def sil_rw(qqid,groupid):
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        sqqid = str(qqid)
        cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT, flag TEXT)')
        last_sil_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        insert_query = "INSERT INTO blocked(qqid,groupid,禁言时间,flag) VALUES (?, ?, ?, ?)"
        data_to_insert = (qqid, groupid,last_sil_time,0)
        cs_.execute(insert_query, data_to_insert)
        sil_db.commit()

        await asyncio.sleep(1)

@sv.on_fullmatch('nssb','复活吧')
async def nssb_(bot,ev):
    ev_cache = ev
    s_qqid = ev.user_id
    s_groupid = ev.group_id
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT ,flag TEXT)')
        cs_.execute(f"SELECT * FROM blocked WHERE flag = 1 AND groupid = {s_groupid}")
        s_result1 = cs_.fetchall()
        if not s_result1:
            await bot.send(ev,'该群暂时没有人因为指令被禁言！')
        else:          
            for result in s_result1:
                ev.group_id = result[1]
                ev.user_id= result[0]
                await util.silence(ev, 0)
            cs_.execute(f"DELETE FROM blocked WHERE flag = 1 AND groupid = {s_groupid}")
            sil_db.commit()
            await bot.send(ev_cache,f"群友正在复活。。。。。。")
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
    with sqlite3.connect(rank_path) as rank_db:
        cs_ = rank_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS rank (qqid TEXT, flag TEXT)')
        cs_.execute(f"SELECT * FROM rank WHERE qqid = {qqid}")
        rank_result = cs_.fetchall()
        if not rank_result:
            await asyncio.sleep(1)
        else:
            for result in rank_result:
                r_adder = int(result[1]) + 1
                insert_query = "INSERT INTO rank(qqid, flag) VALUES (?, ?)"
                data_to_insert = (qqid,str(r_adder))
                cs_.execute(insert_query, data_to_insert)
                rank_db.commit()
            await asyncio.sleep(1)


@sv.on_fullmatch('nssbr')
async def neeb_rank(bot,ev):
    mlist = await bot.get_group_member_list(group_id=ev.group_id)
    with sqlite3.connect(rank_path) as rank_db:
        cs_ = rank_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS rank (qqid TEXT, flag TEXT)')  #保险
        cs_.execute('SELECT * FROM rank WHERE ')
        rank_result = cs_.fetchall()
        if not rank_result:
            await asyncio.sleep(1)
        else:    
            rankcache = sorted(rank_result, key=lambda x : int(x[1]), reverse=True)
            l = len(rankcache) if len(rankcache) < 10 else 10
            msg='救人排行表TOP10：'
            ct = 0
            for ct in range(l) :
                for rank in rankcache:
                    for m in mlist:
                        if rank[0] == m['card']:
                            msg += f"{m['nickname']}救人次数：{rank[1]}"
                ct += 1
            await bot.send(ev,msg)



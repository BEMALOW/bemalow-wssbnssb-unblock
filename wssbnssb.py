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

async def sil_rw(qqid,groupid,time):       #写入部分  相关禁言插件只需调用这部分即可
    with sqlite3.connect(file_path) as sil_db:   #打开file_path的db文件 不存在就创建
        cs_ = sil_db.cursor()

        last_sil_time = datetime.now()    #获取当前时间
        last_sil_time_cache = last_sil_time
        scheduled_time_end = last_sil_time + timedelta(seconds=time)   #计划任务时间 超过这个时间 被禁言的人会被自动解禁 标志自动变换
        next_day_limit = last_sil_time.replace(hour=4, minute=0, second=0, microsecond=0) + timedelta(days=1)
        today_limit = last_sil_time.replace(hour=4, minute=0, second=0, microsecond=0 )       #初始化写入时间、禁言时间、今日和明日清标志时间（）

        scheduled_time = scheduled_time_end.strftime("%Y-%m-%d %H:%M:%S")
        last_sil_time = last_sil_time.strftime("%Y-%m-%d %H:%M:%S")

        cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT, flag TEXT)')   #flag为是否已发送“wssb”标志以及是否可以通过bot解禁的标志 默认为0（禁言）
        insert_query = "INSERT INTO blocked(qqid,groupid,禁言时间,flag) VALUES (?, ?, ?, ?)"     #上面这行是创建表 不存在就新建
        data_to_insert = (qqid, groupid,last_sil_time,0)
        cs_.execute(insert_query, data_to_insert)
        sil_db.commit()   #保存更改 没有这部操作不会保存在硬盘中

        if scheduled_time_end <= next_day_limit:       #如果计划解除禁言时间未超过次日4点                         
            if last_sil_time_cache <= today_limit:     #如果触发禁言时间未超过当日4点
                if scheduled_time_end <= today_limit:   #如果计划解除禁言时间未超过当日四点
                    await add_scheduled(last_sil_time,scheduled_time)    #创建计划任务
            else:
                await add_scheduled(last_sil_time,scheduled_time)    #自动变换标志的计划任务判断  因为每天的4点会自动清  为了减少计划任务数量设计

                
        await asyncio.sleep(1)

async def add_scheduled(s_time,time):               #创建计划任务函数 
    scheduler.add_job(time_to_delete, 'date', run_date=time, args=(s_time,))
    if not scheduler.running:    #如果计划任务已在运行就不会再添加实例
        scheduler.start()
    await asyncio.sleep(1)

async def time_to_delete(search_time):       #计划请标志任务函数  被上方计划任务调用
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        cs_.execute('CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT, flag TEXT)')
        cs_.execute("UPDATE blocked SET flag = '1' WHERE 禁言时间 = ? ;",(search_time,))
        sil_db.commit()
    await asyncio.sleep(1)

@sv.on_fullmatch('nssb','复活吧')     #解禁
async def nssb_(bot,ev):
    ev_cache = ev
    s_qqid = ev.user_id  #获取触发者qq号以及群号
    s_groupid = ev.group_id
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        cs_.execute('CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT ,flag TEXT)')
        cs_.execute(f"SELECT * FROM blocked WHERE flag = 1 AND groupid = {s_groupid}")    #查找标志已变成 1 的该群号成员
        s_result1 = cs_.fetchall()
        if not s_result1:
            await wssb_check(bot,ev)      #如果没有任何改变标志的群员 跳转该函数 
        else:          
            for result in s_result1:
                ev.group_id = result[1]
                ev.user_id= result[0]    #如果有  修改ev数据  解除禁言
                await util.silence(ev, 0)
            cs_.execute(f"DELETE FROM blocked WHERE flag = 1 AND groupid = {s_groupid}")   #删除已经解禁的群成员数据
            sil_db.commit()
            await bot.send(ev_cache,f"群友正在复活。。。。。。")
            await wssb_check(bot,ev)
            await rank_rw(s_qqid)   #写入解救rank函数




@on_command('wssb')
async def wssb_(ev):    #自助解禁服务
    s_qqid = str(ev.event['user_id'])
    with sqlite3.connect(file_path) as sil_db:

        cs_ = sil_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT ,flag TEXT)')
        cs_.execute(f"SELECT * FROM blocked WHERE qqid = {s_qqid}")   #查找数据库中是否存在私聊者数据
        s_result1 = cs_.fetchall()

        if not s_result1:
            await ev.finish('你没有被禁言')   #不存在回复
        else:
            msg=''
            for result in s_result1:
                msg += f'你被禁言的群：{result[1]}，上次被禁言是：{result[2]}。'   #存在就回复
                ev.event.group_id = result[1] 

            cs_.execute("UPDATE blocked SET flag = '1' WHERE qqid = ? ;",(s_qqid,))  #更改标志 从0变为1
            sil_db.commit()  #保存更改
            msg += '请等待管理员送至重生信标'
            await ev.finish(msg)


async def rank_rw(qqid):   #排行榜写入
    with sqlite3.connect(file_path) as rank_db:
        cs_ = rank_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS rank (qqid TEXT, flag TEXT)') #打开表 不存在就新建
        cs_.execute(f"SELECT * FROM rank WHERE qqid = {qqid}")   #查找解救者的数据
        rank_result = cs_.fetchall()
        if not rank_result:
            insert_query = "INSERT INTO rank(qqid, flag) VALUES (?, ?)"  #不存在就新增数据
            data_to_insert = (qqid,1)
            cs_.execute(insert_query, data_to_insert)
            rank_db.commit()
            await asyncio.sleep(1)
        else:
            for result in rank_result:
                r_adder = int(result[1]) + 1
                insert_query = "UPDATE rank SET flag = ? WHERE qqid = ? ;"  #存在就使次数加一
                data_to_insert = (str(r_adder),qqid,)
                cs_.execute(insert_query, data_to_insert)
                rank_db.commit()
            await asyncio.sleep(1)


@sv.on_fullmatch('nssbr')   
async def neeb_rank(bot,ev):  #查询排行榜
    mlist = await bot.get_group_member_list(group_id=ev.group_id)  #获取所在群的数据列表
    with sqlite3.connect(file_path) as rank_db:
        cs_ = rank_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS rank (qqid TEXT, flag TEXT)')  #保险 打开表 不存在就新建
        cs_.execute('SELECT * FROM rank') #选择rank一列的所有数据
        rank_result = cs_.fetchall()
        if not rank_result:
            await asyncio.sleep(1)  #如果没有就没有反应
        else:    
            rankcache = sorted(rank_result, key=lambda x : int(x[1]), reverse=True)
            msg='救人排行表TOP10：\n'
            for rank in rankcache[:10]:#前十的数据
                for m in mlist:
                    if int(rank[0])== int(m['user_id']): #判断rank一列数据的qqid是否有群列表中相同的
                        msg += f"{m['nickname']}救人次数：{rank[1]}\n" #有就添加他的昵称和次数到待发送消息中
            await bot.send(ev,msg)



async def wssb_check(bot,ev):   #判断数据库中对应群聊是否还有未私发bot"wssb"解禁的成员
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
async def wssb_autoclean():           #每日定时清除的计划任务  调用hoshino的模块
    with sqlite3.connect(file_path) as sil_db:
        cs_ = sil_db.cursor()
        cs_.execute( 'CREATE TABLE IF NOT EXISTS blocked (qqid TEXT, groupid TEXT, 禁言时间 TEXT ,flag TEXT)')
        cs_.execute("UPDATE blocked SET flag = '1' ")
        sil_db.commit()
    await asyncio.sleep(1)

@sv.on_notice('group_ban')
async def wssb_claen(ev):           #额外模块  判断群员是否被 其他管理员/群主 禁言
    qqid = ev.event['user_id']
    groupid = ev.event['group_id']
    if ev.event['sub_type'] == "ban" and ev.event['user_id'] != 0:
        with sqlite3.connect(file_path) as sil_db:     #数据 是否 写入部分同上方相同  后续应合并相同部分以减少代码长度

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
            if not s_result0 and ev.event['sub_type'] == "lift_ban":      #解禁时 数据库中是否含有未解禁成员的数据（待优化  这条应该用不上）
                await ev.send("该群现在暂时没有人被禁言！")
            else:
                if ev.event['sub_type'] == "ban" and ev.event['user_id'] == 0:               #管理员/群主 开启了全员禁言  自动删除该群所有禁言记录
                    cs_.execute(f"DELETE FROM blocked WHERE groupid = {s_groupid}")
                    sil_db.commit()
                    await ev.send("大赦天下。")
                if ev.event['sub_type'] == "lift_ban" and ev.event['user_id'] != 0:                #检测管理员/群主手动解禁标志   只要解禁一个人  该群所有人的标志自动变为1
                    cs_.execute("UPDATE blocked SET flag = '1' WHERE groupid = ? ;",(s_groupid,))
                    sil_db.commit()
                    await ev.send("管理已将被禁言的群友变为复活旗帜,请输入'nssb'复活他们。")

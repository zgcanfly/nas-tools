import os
import signal
import sys
import warnings
import log
from config import Config
from app.brushtask import BrushTask
from app.sync import run_monitor, stop_monitor
from app.scheduler import run_scheduler, stop_scheduler
from app.utils.check_config import check_config
from app.utils.system_utils import SystemUtils
from app.utils.types import OsType
from version import APP_VERSION
from web.app import FlaskApp
from web.backend.web_utils import init_features


# 添加第三方库入口
third_party = ['feapder',
               'qbittorrent-api',
               'transmission-rpc',
               'anitopy',
               'plexapi',
               'python-opensubtitles',
               'cn2an']
for third_party_lib in third_party:
    sys.path.append(os.path.join(os.path.dirname(__file__), "third_party", third_party_lib).replace("\\", "/"))


warnings.filterwarnings('ignore')

# 运行环境判断
is_windows_exe = getattr(sys, 'frozen', False) and (os.name == "nt")
if is_windows_exe:
    # 托盘相关库
    import threading
    from windows.trayicon import trayicon

    # 初始化环境变量
    os.environ["NASTOOL_CONFIG"] = os.path.join(os.path.dirname(sys.executable), "config", "config.yaml").replace("\\",
                                                                                                                  "/")
    os.environ["NASTOOL_LOG"] = os.path.join(os.path.dirname(sys.executable), "config", "logs").replace("\\", "/")
    try:
        os.makedirs(os.path.join(os.path.dirname(sys.executable), "config").replace("\\", "/"))
    except Exception as err:
        print(err)


def sigal_handler(num, stack):
    if SystemUtils.get_system() == OsType.LINUX and SystemUtils.check_process("supervisord"):
        print(str(stack))
        log.warn('捕捉到退出信号：%s，开始退出...' % num)
        # 停止定时服务
        stop_scheduler()
        # 停止监控
        stop_monitor()
        # 退出主进程
        sys.exit()


if __name__ == "__main__":

    # 参数
    os.environ['TZ'] = 'Asia/Shanghai'
    log.console("配置文件地址：%s" % os.environ.get('NASTOOL_CONFIG'))
    log.console('NASTool 当前版本号：%s' % APP_VERSION)

    # 检查配置文件
    config = Config()
    if not check_config(config):
        sys.exit()

    # 启动进程
    log.console("开始启动进程...")

    # 退出事件
    signal.signal(signal.SIGINT, sigal_handler)
    signal.signal(signal.SIGTERM, sigal_handler)

    # 启动定时服务
    run_scheduler()

    # 启动监控服务
    run_monitor()

    # 启动刷流服务
    BrushTask()

    # 启动托盘
    if is_windows_exe:
        homepage_port = config.get_config('app').get('web_port')
        log_path = os.environ.get("NASTOOL_LOG")


        def traystart():
            tray = trayicon(homepage_port, log_path)


        p1 = threading.Thread(target=traystart, daemon=True)
        p1.start()

    # 加载特性
    init_features()

    # 启动主WEB服务
    FlaskApp().run_service()

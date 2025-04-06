@echo off
REM 设置虚拟环境名称
set ENV_NAME=auto_trade_env_py310

REM 检查并删除现有虚拟环境
echo 检查并删除现有虚拟环境...
conda deactivate
conda remove --name %ENV_NAME% --all --yes

REM 创建新的虚拟环境
echo 创建新的虚拟环境...
conda create --name %ENV_NAME% python=3.10 --yes

REM 激活虚拟环境
echo 激活虚拟环境...
call conda activate %ENV_NAME%

REM 安装依赖
echo 安装依赖...
pip install -r requirements.txt

REM 使用 conda 安装 ta-lib
echo 使用 conda 安装 ta-lib...
conda install -c conda-forge ta-lib --yes

REM 检查 tigeropen 是否安装成功
echo 检查 tigeropen 是否安装成功...
pip show tigeropen
if errorlevel 1 (
    echo tigeropen 未安装，尝试单独安装...
    pip install tigeropen
)

REM 检查 scikit-learn 是否安装成功
echo 检查 scikit-learn 是否安装成功...
pip show scikit-learn
if errorlevel 1 (
    echo scikit-learn 未安装，尝试单独安装...
    pip install scikit-learn
)

REM 运行程序
echo 运行程序...
python main.py --stop-loss

REM 保持窗口打开
pause

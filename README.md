# 项目说明

## 数据要求

flux数据中必须有以下列

record_time

co2_flux - CO2通量

h2o_flux - H2O通量

le - 潜热通量

h - 显热通量

record_time要求能被`pd.to_datetime()`解析，以下格式都可以

```
2024-01-01 12:30:00

2024/01/01 12:30:00

01-01-2024 12:30:00

2024-01-01T12:30:00
```



## 打包说明

`python -m PyInstaller --clean build.spec`

dist根目录的exe是单文件版本，可以直接运行

下一级目录中的exe文件，是启动器，环境在同级文件夹中
# 项目说明

## 数据要求


时间列名必须是 `record_time`

要求能被`pd.to_datetime()`解析

```
2024-01-01 12:30:00

2024/01/01 12:30:00

01-01-2024 12:30:00

2024-01-01T12:30:00
```

## 打包说明

`python -m PyInstaller --clean build.spec`
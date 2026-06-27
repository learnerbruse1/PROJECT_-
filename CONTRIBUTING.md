# 贡献指南

感谢参与「洪山区人口分布热力与公共设施叠加分析系统」。本文档说明开发环境、协作流程与代码规范。

## 一、开发环境

| 工具 | 版本 |
| --- | --- |
| Node.js | ≥ 20（推荐 22，见 `.nvmrc`） |
| Python | ≥ 3.11（推荐 3.12） |
| npm | ≥ 10 |

```bash
# 安装依赖（前后端一次到位）
npm run setup

# 一键启动前后端（http://localhost:5173）
npm start
```

仅起单边：`npm run backend` / `npm run frontend`。详见 [README](README.md) 与 [docs/开发者文档.md](docs/开发者文档.md)。

## 二、目录与职责

代码改动前请先读 [docs/开发者文档.md](docs/开发者文档.md)（含全量文件清单）。三条架构边界请遵守：

- 前端组件只读写 `frontend/src/stores/mapStore.js`；
- 所有后端调用只走 `frontend/src/api.js`；
- 后端路由只依赖 `backend/app/db/provider.py`，不直接 import 具体数据后端。

## 三、分支与提交

- 从 `main` 切功能分支：`feat/xxx`、`fix/xxx`、`docs/xxx`、`refactor/xxx`。
- 提交信息建议遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
  `feat(frontend): 新增等时圈图层`、`fix(backend): 修正盲区面积单位`。
- PR 需说明动机、改动点、自测情况；UI 改动请附截图。

## 四、代码规范

- 统一编码 UTF-8、LF 换行、2 空格缩进（前端）/ 4 空格（Python），见 `.editorconfig`。
- 前端：Vue3 `<script setup>`；新增后端接口先在 `api.js` 封装。
- 后端：保持文件后端与 PostGIS 后端**函数签名与返回结构一致**，否则路由层取不到字段。
- 注释与界面文案使用中文，与现有风格保持一致。

## 五、提交前自查

```bash
npm run build                       # 前端可正常构建
cd backend && python -c "import app.main"   # 后端可正常导入
```

并手动跑通：地图加载、热力、设施点选、覆盖区、盲区、供需面板。

## 六、数据

`data/processed/` 为系统运行所需成果数据（已跟踪）；`data/raw/` 为源数据（`.gitignore` 排除，可由 `scripts/栅格重采样.py` 再生）。新增大文件请勿提交到 `data/processed/` 以外位置，详见 [data/README.md](data/README.md)。

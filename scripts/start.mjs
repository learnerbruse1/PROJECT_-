// 一键启动脚本：同时拉起后端（FastAPI/uvicorn）与前端（Vite）。
// 纯 Node 内置模块实现，无需安装任何依赖；跨平台（Windows / macOS / Linux）。
//   npm start      启动前后端
//   Ctrl + C       一并退出
import { spawn, execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const isWin = process.platform === 'win32'

// ---------- 依赖检查 ----------
function checkDependencies() {
  const missing = []
  const PY = process.env.PYTHON || 'python'
  const FRONTEND_NM = join(ROOT, 'frontend', 'node_modules')

  // 前端
  if (!existsSync(join(FRONTEND_NM, 'vite'))) {
    missing.push('前端依赖 (frontend/node_modules)')
  }

  // 后端（通过 python -c 批量导入检测）
  try {
    execSync(`"${PY}" -c "import fastapi, uvicorn, pydantic, asyncpg, shapely"`, {
      stdio: 'pipe',
      timeout: 10_000,
    })
  } catch {
    missing.push('后端 Python 依赖 (fastapi, uvicorn, pydantic, asyncpg, shapely)')
  }

  if (missing.length > 0) {
    process.stderr.write(
      `\n  \x1b[31m✗\x1b[0m 缺少以下依赖：\n${missing.map((m) => `    - ${m}`).join('\n')}\n` +
        `\n  请先运行 \x1b[33mnpm run setup\x1b[0m 安装全部依赖，再重新启动。\n\n`,
    )
    process.exit(1)
  }
}
// ------------------------------------

// ---------- .env 自动同步 ----------
// 当 .env.example 发生变化时，自动创建/更新 .env：
//   - 新增的键 → 从 .env.example 写入
//   - 已有的键 → 保留用户在 .env 中的自定义值不变
const ENV_EXAMPLE = join(ROOT, 'frontend', '.env.example')
const ENV_FILE = join(ROOT, 'frontend', '.env')
const SYNC_MARKER = '# _SYNC_HASH='

function parseDotEnv(path) {
  if (!existsSync(path)) return {}
  const map = {}
  const content = readFileSync(path, 'utf-8')
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    const val = trimmed.slice(eq + 1).trim()
    if (key) map[key] = val
  }
  return map
}

function syncEnvFile() {
  if (!existsSync(ENV_EXAMPLE)) return // 没有模板则跳过

  const exampleHash = createHash('sha256').update(readFileSync(ENV_EXAMPLE, 'utf-8')).digest('hex').slice(0, 16)

  // 无 .env → 直接复制
  if (!existsSync(ENV_FILE)) {
    const content = readFileSync(ENV_EXAMPLE, 'utf-8') + `\n${SYNC_MARKER}${exampleHash}\n`
    writeFileSync(ENV_FILE, content, 'utf-8')
    process.stdout.write('  \x1b[32m✓\x1b[0m 已从 .env.example 创建 .env\n')
    return
  }

  // 检查是否需要同步
  const envContent = readFileSync(ENV_FILE, 'utf-8')
  const trackedHash = (envContent.match(new RegExp(`^${SYNC_MARKER.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\S+)`, 'm')) || [])[1]
  if (trackedHash === exampleHash) return // 未变化，跳过

  // .env.example 已变更 → 合并：新增键，保留已有值
  const exampleEntries = parseDotEnv(ENV_EXAMPLE)
  const existingEntries = parseDotEnv(ENV_FILE)

  let added = 0
  const lines = envContent.split(/\r?\n/)
  for (const [key, val] of Object.entries(exampleEntries)) {
    if (key in existingEntries) continue // 用户已设置，保留
    lines.push(`${key}=${val}`)
    added++
  }

  // 更新同步哈希
  const markerIdx = lines.findIndex(l => l.startsWith(SYNC_MARKER))
  if (markerIdx >= 0) {
    lines[markerIdx] = `${SYNC_MARKER}${exampleHash}`
  } else {
    lines.push(`${SYNC_MARKER}${exampleHash}`)
  }

  writeFileSync(ENV_FILE, lines.join('\n'), 'utf-8')
  if (added > 0) {
    process.stdout.write(`  \x1b[32m✓\x1b[0m .env.example 已变更，自动同步了 ${added} 个新键到 .env\n`)
  } else {
    process.stdout.write('  \x1b[32m✓\x1b[0m .env.example 已变更，.env 无需新增键\n')
  }
}
// ------------------------------------

// ---------- 天地图密钥提醒 ----------
function checkTiandituKey() {
  const env = parseDotEnv(ENV_FILE)
  const key = env.VITE_TIANDITU_KEY || ''
  if (!key.trim()) {
    process.stdout.write(
      `\n  \x1b[33m⚠\x1b[0m 未配置天地图密钥（VITE_TIANDITU_KEY），底图将回退到 OpenStreetMap。\n` +
        `    OSM 瓦片在国内可能加载缓慢或无法显示。\n` +
        `    如需天地图底图，请前往 \x1b[36mhttps://console.tianditu.gov.cn/\x1b[0m 申请密钥，\n` +
        `    并填入 \x1b[33mfrontend/.env\x1b[0m 中的 VITE_TIANDITU_KEY。\n\n`,
    )
  }
}
// ------------------------------------
const PY = process.env.PYTHON || 'python'
const BACKEND_PORT = process.env.BACKEND_PORT || '8000'
const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173'

const children = []
let shuttingDown = false

function run(name, color, command, cwd) {
  const prefix = `\x1b[${color}m[${name}]\x1b[0m `
  const child = spawn(command, { cwd, shell: true, env: process.env })

  const pipe = (stream, out) => {
    let buf = ''
    stream.on('data', (chunk) => {
      buf += chunk.toString()
      const lines = buf.split(/\r?\n/)
      buf = lines.pop()
      for (const line of lines) out.write(prefix + line + '\n')
    })
  }
  pipe(child.stdout, process.stdout)
  pipe(child.stderr, process.stderr)

  child.on('exit', (code) => {
    process.stdout.write(prefix + `已退出（code ${code}）\n`)
    shutdown(code || 0)
  })
  child.on('error', (err) => {
    process.stderr.write(prefix + `启动失败：${err.message}\n`)
    shutdown(1)
  })
  children.push(child)
}

function shutdown(code = 0) {
  if (shuttingDown) return
  shuttingDown = true
  for (const c of children) {
    if (!c.pid) continue
    try {
      // Windows 下需结束整个进程树（uvicorn --reload / vite 会派生子进程）
      if (isWin) spawn('taskkill', ['/pid', String(c.pid), '/T', '/F'], { stdio: 'ignore' })
      else c.kill('SIGTERM')
    } catch {
      /* ignore */
    }
  }
  setTimeout(() => process.exit(code), 600)
}

process.on('SIGINT', () => shutdown(0))
process.on('SIGTERM', () => shutdown(0))

checkDependencies()
syncEnvFile() // 根据 .env.example 自动创建/更新 .env
checkTiandituKey()
console.log('\n  正在启动洪山区人口热力与公共设施叠加系统…\n')
run('后端', '36', `${PY} -m uvicorn app.main:app --reload --host 127.0.0.1 --port ${BACKEND_PORT}`, join(ROOT, 'backend'))
run('前端', '32', 'npm run dev', join(ROOT, 'frontend'))
console.log(
  `\n  前端  http://localhost:${FRONTEND_PORT}\n` +
    `  后端  http://localhost:${BACKEND_PORT}/docs\n\n  按 Ctrl + C 退出。\n`,
)

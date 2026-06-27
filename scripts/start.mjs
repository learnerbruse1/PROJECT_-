// 一键启动脚本：同时拉起后端（FastAPI/uvicorn）与前端（Vite）。
// 纯 Node 内置模块实现，无需安装任何依赖；跨平台（Windows / macOS / Linux）。
//   npm start      启动前后端
//   Ctrl + C       一并退出
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const isWin = process.platform === 'win32'
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

console.log('\n  正在启动洪山区人口热力与公共设施叠加系统…\n')
run('后端', '36', `${PY} -m uvicorn app.main:app --reload --host 127.0.0.1 --port ${BACKEND_PORT}`, join(ROOT, 'backend'))
run('前端', '32', 'npm run dev', join(ROOT, 'frontend'))
console.log(
  `\n  前端  http://localhost:${FRONTEND_PORT}\n` +
    `  后端  http://localhost:${BACKEND_PORT}/docs\n\n  按 Ctrl + C 退出。\n`,
)

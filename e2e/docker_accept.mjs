// Docker 验收 — 浏览器侧(Playwright + Edge)
// 运行: node docker_accept.mjs <ACCESS_TOKEN>
import { chromium } from "playwright";
import fs from "fs";

const BASE = "http://localhost:8002";
const TOKEN = process.argv[2];
const results = [];
let pass = 0, fail = 0;

function check(name, ok, detail = "") {
  results.push({ name, ok, detail });
  ok ? pass++ : fail++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  | " + detail : ""}`);
}

const browser = await chromium.launch({ channel: "msedge", headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const page = await ctx.newPage();
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// ---- 1. 无 token → 登录遮罩(#8) ----
await page.goto(BASE, { waitUntil: "domcontentloaded" });
await page.waitForSelector("#login-mask:not(.hidden)", { timeout: 8000 }).then(
  () => check("#8a 无token显示登录页", true),
  () => check("#8a 无token显示登录页", false, "login-mask 未显示")
);

// ---- 2. 错误 token → 登录失败提示(#8) ----
await page.fill("#token-input", "wrong-token-123");
await page.click("#login-btn");
await page.waitForSelector("#login-error:not(.hidden)", { timeout: 5000 }).then(
  () => check("#8b 错token提示失败", true),
  () => check("#8b 错token提示失败", false, "login-error 未显示")
);

// ---- 3. 正确 token → 进入应用 + 会话加载(#8) ----
await page.fill("#token-input", TOKEN);
await page.click("#login-btn");
await page.waitForSelector("#app:not(.hidden)", { timeout: 5000 }).then(
  async () => {
    check("#8c 正确token进入应用", true);
    await page.waitForSelector("#session-list li", { timeout: 5000 }).then(
      () => check("#5 会话列表加载(持久化)", true),
      () => check("#5 会话列表加载(持久化)", false, "无会话项")
    );
  },
  () => check("#8c 正确token进入应用", false, "app 未显示")
);

// ---- 4. 空输入按钮禁用(#1) ----
const btnStateEmpty = await page.$eval("#send-btn", el => el.disabled);
check("#1 空输入发送按钮禁用", btnStateEmpty === true, `disabled=${btnStateEmpty}`);
await page.fill("#question", "测试文字");
await sleep(300);
const btnStateTyped = await page.$eval("#send-btn", el => el.disabled);
check("#1b 输入后按钮可用", btnStateTyped === false, `disabled=${btnStateTyped}`);

// ---- 5. 回答中按钮禁用 + delta 渲染(#3) ----
let doneFired = false;
await page.route("**/api/chat", async route => {
  const chunks = [
    `event: delta\ndata: {"type":"delta","text":"这是模拟的"}\n\n`,
    `event: delta\ndata: {"type":"delta","text":"流式回答"}\n\n`,
    `event: sources\ndata: {"type":"sources","names":["三北防护林遥感监测技术要点.txt"]}\n\n`,
    `event: done\ndata: {"type":"done"}\n\n`,
  ];
  await sleep(2500); // 模拟回答中的等待窗口
  await route.fulfill({
    status: 200,
    contentType: "text/event-stream",
    headers: { "Access-Control-Allow-Origin": "*" },
    body: chunks.join(""),
  });
});
await page.click("#send-btn");
await sleep(500);
const midDisabled = await page.$eval("#send-btn", el => el.disabled);
check("#3 回答中发送按钮禁用", midDisabled === true, `disabled=${midDisabled}`);
await sleep(3000); // 等待 mock 2.5s 交付完成 + 前端渲染
const msgText = await page.$eval("#messages", el => el.innerText);
check("#3b 流式delta渲染", msgText.includes("流式回答"), msgText.slice(0, 60).replace(/\n/g, " "));
const btnAfter = await page.$eval("#send-btn", el => el.disabled);
check("#3c 完成后按钮恢复", btnAfter === false, `disabled=${btnAfter}`);
const srcTag = await page.$eval("#messages", el => el.innerText);
check("#7 引用标签渲染", srcTag.includes("三北防护林遥感监测技术要点"), "source-tag");

// ---- 6. 断网 → 错误条不白屏(#4) ----
await page.unroute("**/api/chat");
await page.route("**/api/chat", route => route.abort("connectionfailed"));
await page.fill("#question", "断网测试");
await page.click("#send-btn");
await sleep(1200);
const errBar = await page.$eval("#messages", el => el.innerText.includes("error-bar") || el.querySelector(".error-bar") !== null);
check("#4 断网显示错误条不白屏", errBar, await page.$eval("#messages", el => (el.querySelector(".error-bar") || {}).textContent || ""));
await page.unroute("**/api/chat");

// ---- 7. 真实提问 → 余额不足错误条(#10) ----
await page.$eval("#messages", el => el.querySelectorAll(".error-bar").forEach(b => b.remove()));
await page.fill("#question", "吉林省三北防护林遥感监测的重点指标有哪些?");
await page.click("#send-btn");
let realErr = "";
for (let i = 0; i < 16 && !realErr; i++) {
  await sleep(3000);
  realErr = await page.$eval("#messages", el => {
    const bar = el.querySelector(".error-bar");
    return bar ? bar.textContent : "";
  });
}
check("#10 上游异常错误条显示", realErr.length > 0, realErr.slice(0, 60));
const appVisible = await page.$eval("#app", el => !el.classList.contains("hidden"));
check("#10b 页面不白屏", appVisible === true);

// ---- 8. 文档面板(#7) ----
await page.click("#docs-btn");
await sleep(1200);
const docs = await page.$eval("#docs-list", el => el.innerText);
check("#7b 文档列表显示", docs.includes("三北防护林遥感监测技术要点.txt"), docs.split("\n").length + " 项");

await browser.close();
fs.writeFileSync("e2e_result.json", JSON.stringify(results, null, 2));
console.log(`\n==== ${pass} passed, ${fail} failed ====`);
process.exit(fail ? 1 : 0);

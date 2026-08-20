const { test, expect } = require('@playwright/test');

test('verify live dashboard WebSocket telemetry and style changes', async ({ page }) => {
  page.on('console', msg => {
    console.log(`[CONSOLE] [${msg.type()}] ${msg.text()}`);
  });

  page.on('pageerror', err => {
    console.log(`[UNCAUGHT_ERROR] ${err.toString()}`);
  });

  console.log('Navigating to http://localhost:3000/dashboard...');
  await page.goto('http://localhost:3000/dashboard', { waitUntil: 'domcontentloaded' });

  console.log('Waiting 60 seconds for WebSocket packets...');
  await page.waitForTimeout(60000);

  console.log('Taking screenshot of dashboard...');
  await page.screenshot({ path: 'C:/Users/bari2/.gemini/antigravity-ide/brain/80cfda19-dec4-483c-9631-bfbef5f535c1/dashboard_live_verify.png' });
});

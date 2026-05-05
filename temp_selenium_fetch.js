
const { chromium } = require('selenium-webdriver');

(async () => {
    const driver = await chromium.launch({ headless: true });
    
    // Navigate to TWSE margin page
    await driver.get('https://www.twse.com.tw/zh/trading/margin/mi-margn.html');
    
    // Wait for page to load
    await driver.sleep(3000);
    
    // Get page source
    const html = await driver.pageSource();
    
    // Write to temp file
    const fs = require('fs');
    fs.writeFileSync('twse_margin_temp.html', html);
    
    console.log('HTML saved, length:', html.length);
    
    await driver.quit();
})();

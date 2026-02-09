const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({
        headless: false,
        slowMo: 1000
    });

    const page = await browser.newPage();

    // Listen for console messages and errors
    page.on('console', msg => {
        const type = msg.type();
        const text = msg.text();
        console.log(`[Browser Console ${type}]: ${text}`);
    });

    page.on('pageerror', error => {
        console.error(`[Browser JavaScript Error]:`, error.message);
        console.error(`Stack:`, error.stack);
    });

    // Navigate to the HTML file
    const filePath = 'file:///Users/alexchong/AI/MinerU/temp/IQC_Report_20260209_070307.html';
    console.log(`\n🔍 Opening: ${filePath}\n`);

    await page.goto(filePath);

    // Wait for page to load
    await page.waitForTimeout(3000);

    // Check if raw data table exists and has content
    const rawDataTable = await page.locator('#raw-data-content').evaluate(el => {
        return {
            exists: !!el,
            innerHTML: el ? el.innerHTML.substring(0, 500) : 'NOT FOUND',
            hasTable: el ? el.querySelector('table') !== null : false
        };
    });

    console.log('\n📊 Raw Data Table Status:');
    console.log(JSON.stringify(rawDataTable, null, 2));

    // Check iqcData structure
    const iqcDataCheck = await page.evaluate(() => {
        return {
            hasIqcData: typeof window.iqcData !== 'undefined',
            dimensionsCount: window.iqcData ? window.iqcData.dimensions.length : 0,
            firstDimMeasurements: window.iqcData && window.iqcData.dimensions[0] ? {
                name: window.iqcData.dimensions[0].name,
                measurementsLength: window.iqcData.dimensions[0].measurements.length,
                first3Measurements: window.iqcData.dimensions[0].measurements.slice(0, 3)
            } : null
        };
    });

    console.log('\n📋 IQC Data Structure:');
    console.log(JSON.stringify(iqcDataCheck, null, 2));

    // Check if renderReport was called
    const renderReportStatus = await page.evaluate(() => {
        return {
            hasRendered: window.hasRendered,
            renderReportExists: typeof window.renderReport === 'function'
        };
    });

    console.log('\n🖥️ Render Report Status:');
    console.log(JSON.stringify(renderReportStatus, null, 2));

    console.log('\n⏸️ Pausing for 10 seconds for manual inspection...');
    console.log('🔍 Check the browser DevTools console (F12) for any errors\n');

    await page.waitForTimeout(10000);

    await browser.close();
})();

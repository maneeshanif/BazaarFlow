/* eslint-disable @typescript-eslint/no-require-imports */
const axios = require('axios');

async function run() {
  try {
    const payload = {
      customer_name: 'Integration Test',
      customer_phone: '+923001234567',
      product_id: 'sku-int-1',
      product_name: 'Integration Product',
      quantity: 1,
      budget: '1000-2000',
      payment_status: 'pending',
      delivery_address: 'Test City',
      notes: 'Automated test',
    };

    console.log('Posting to http://localhost:8000/api/sales ...');
    const res = await axios.post('http://localhost:8000/api/sales', payload, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 5000,
    });

    console.log('Response status:', res.status);
    if (res.status === 201) {
      console.log('Integration test succeeded — created order id:', res.data.order.id);
      process.exit(0);
    } else {
      console.error('Unexpected status code', res.status);
      process.exit(2);
    }
  } catch (err) {
    console.error('Integration test failed:', err.message || err);
    if (err.response) {
      console.error('Response data:', err.response.data);
    }
    process.exit(1);
  }
}

run();

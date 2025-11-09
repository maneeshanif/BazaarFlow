const axios = require('axios');

async function run() {
  try {
    console.log('Testing chat endpoint at http://localhost:8000/api/chat/sales ...');
    
    // Test 1: Basic chat message
    const payload1 = {
      message: 'Hello, what products do you have?',
      session_id: 'test_session_1'
    };

    const response1 = await axios.post('http://localhost:8000/api/chat/sales', payload1, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000,
    });

    console.log('Response status:', response1.status);
    if (response1.status === 200) {
      console.log('✓ Basic chat test succeeded');
      console.log('Response data:', response1.data);
      
      // Verify response structure
      if (response1.data.response && typeof response1.data.response === 'string') {
        console.log('✓ Response has correct structure');
      } else {
        console.error('✗ Response has incorrect structure');
        process.exit(1);
      }
    } else {
      console.error('✗ Unexpected status code', response1.status);
      process.exit(2);
    }

    // Test 2: Follow-up message to test session continuity
    const payload2 = {
      message: 'Show me the prices for the products you mentioned',
      session_id: 'test_session_1'  // Same session to test continuity
    };

    const response2 = await axios.post('http://localhost:8000/api/chat/sales', payload2, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000,
    });

    console.log('Follow-up response status:', response2.status);
    if (response2.status === 200) {
      console.log('✓ Follow-up message test succeeded');
      console.log('Follow-up response data:', response2.data);
      
      // Verify that session ID is maintained
      if (response2.data.session_id === 'test_session_1') {
        console.log('✓ Session continuity maintained');
      } else {
        console.error('✗ Session continuity failed');
        process.exit(1);
      }
    } else {
      console.error('✗ Follow-up message test failed with status', response2.status);
      process.exit(2);
    }

    // Test 3: Test without session ID to see if one is generated
    const payload3 = {
      message: 'What is your return policy?',
      // No session_id to test auto-generation
    };

    const response3 = await axios.post('http://localhost:8000/api/chat/sales', payload3, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000,
    });

    console.log('Auto-session response status:', response3.status);
    if (response3.status === 200) {
      console.log('✓ Auto-session generation test succeeded');
      console.log('Auto-session response data:', response3.data);
      
      // Verify that a session ID was generated
      if (response3.data.session_id && typeof response3.data.session_id === 'string') {
        console.log('✓ Session ID was auto-generated');
      } else {
        console.error('✗ Session ID was not auto-generated');
        process.exit(1);
      }
    } else {
      console.error('✗ Auto-session generation test failed with status', response3.status);
      process.exit(2);
    }

    console.log('✓ All chat integration tests passed!');
    process.exit(0);

  } catch (err) {
    console.error('Chat integration test failed:', err.message || err);
    if (err.response) {
      console.error('Response data:', err.response.data);
      console.error('Response status:', err.response.status);
    }
    process.exit(1);
  }
}

run();
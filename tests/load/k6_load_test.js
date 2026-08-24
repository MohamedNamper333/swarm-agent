/**
 * k6 Load Test for Swarm Agent Enterprise
 * Tests: Execute, Auth, Memory Search, Job Queue
 * 
 * Run: k6 run tests/load/k6_load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const executionDuration = new Trend('execution_duration_ms');
const authDuration = new Trend('auth_duration_ms');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 VUs
    { duration: '5m', target: 100 },   // Stay at 100 VUs
    { duration: '2m', target: 500 },   // Spike to 500 VUs
    { duration: '5m', target: 500 },   // Stay at 500
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(99)<500'],   // p99 < 500ms
    errors: ['rate<0.01'],              // Error rate < 1%
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const API_TOKEN = __ENV.API_TOKEN || 'test-token';

// Setup: Get authentication token
export function setup() {
  const res = http.post(`${BASE_URL}/auth/token`, JSON.stringify({
    grant_type: 'client_credentials',
    client_id: 'load-test',
    client_secret: 'load-test-secret',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
  
  if (res.status === 200) {
    return { token: res.json('access_token') };
  }
  return { token: API_TOKEN }; // Fallback to test token
}

// Main test scenarios
export default function(data) {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${data.token}`,
    },
  };
  
  // Scenario weights
  const scenario = Math.random();
  
  if (scenario < 0.4) {
    // 40% - Code Execution
    testCodeExecution(params);
  } else if (scenario < 0.7) {
    // 30% - Memory Search
    testMemorySearch(params);
  } else if (scenario < 0.9) {
    // 20% - Job Queue Operations
    testJobQueue(params);
  } else {
    // 10% - Health Checks
    testHealthCheck(params);
  }
}

function testCodeExecution(params) {
  const payload = JSON.stringify({
    question: 'Write a function that returns the sum of two numbers',
    type: 'code',
    tenant_id: 'load-test',
    principal_id: `user-${__VU}`,
  });
  
  const res = http.post(`${BASE_URL}/api/v1/execute`, payload, params);
  
  const success = check(res, {
    'execute status is 200': (r) => r.status === 200,
    'has result': (r) => r.json('output') !== undefined,
  });
  
  executionDuration.add(res.timings.duration);
  errorRate.add(!success);
}

function testMemorySearch(params) {
  const payload = JSON.stringify({
    query: 'binary search algorithm implementation',
    tenant_id: 'load-test',
    top_k: 5,
  });
  
  const res = http.post(`${BASE_URL}/api/v1/memory/search`, payload, params);
  
  const success = check(res, {
    'search status is 200': (r) => r.status === 200,
  });
  
  errorRate.add(!success);
}

function testJobQueue(params) {
  const res = http.get(`${BASE_URL}/api/v1/jobs/status?limit=10`, params);
  
  const success = check(res, {
    'jobs status is 200': (r) => r.status === 200,
  });
  
  errorRate.add(!success);
}

function testHealthCheck(params) {
  const res = http.get(`${BASE_URL}/health`, params);
  
  const success = check(res, {
    'health status is 200': (r) => r.status === 200,
    'health is healthy': (r) => r.json('status') === 'healthy',
  });
  
  errorRate.add(!success);
}

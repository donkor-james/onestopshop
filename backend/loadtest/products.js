// Usage:  k6 run -e BASE_URL=https://your-api.example.com loadtest/products.js
// Record p95 for each configuration (cache off/on, index off/on) and put the
// table in the README. Seed first:  python manage.py seed_products --products 100000
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 25 },
    { duration: '1m', target: 25 },
    { duration: '10s', target: 0 },
  ],
  thresholds: { http_req_failed: ['rate<0.01'], http_req_duration: ['p(95)<300'] },
};

const paths = ['/api/products/', '/api/products/?page=2', '/api/products/?search=seed'];

export default function () {
  const res = http.get(`${__ENV.BASE_URL}${paths[Math.floor(Math.random() * paths.length)]}`);
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(0.2);
}

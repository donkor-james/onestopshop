import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "30s", target: 25 },
    { duration: "1m", target: 25 },
    { duration: "10s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{name:list}": ["p(95)<500"],
    "http_req_duration{name:page2}": ["p(95)<500"],
    "http_req_duration{name:search}": ["p(95)<500"],
  },
};

const targets = [
  { name: "list", path: "/api/products/" },
  { name: "page2", path: "/api/products/?page=2" },
  { name: "search", path: "/api/products/?search=seed" },
];

export default function () {
  const t = targets[Math.floor(Math.random() * targets.length)];
  const res = http.get(`${__ENV.BASE_URL}${t.path}`, {
    tags: { name: t.name },
  });
  check(res, { "status 200": (r) => r.status === 200 });
  sleep(0.2);
}

module.exports = {
  apps: [
    {
      name: "openraven-core",
      cwd: "/home/ubuntu/source/OpenRaven/openraven",
      script: "./start_server.sh",
      interpreter: "/bin/bash",
      watch: false,
      max_restarts: 5,
      restart_delay: 3000,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
    },
    {
      name: "openraven-ui",
      cwd: "/home/ubuntu/source/OpenRaven/openraven-ui",
      script: "./start_server.sh",
      interpreter: "/bin/bash",
      env: {
        PORT: 3002,
        CORE_API_URL: "http://127.0.0.1:8741",
      },
      watch: false,
      max_restarts: 5,
      restart_delay: 3000,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
    },
  ],
};

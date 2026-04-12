import os

with open(".gitignore", "r") as f:
    c = f.read()
c = c.replace("<<<<<<< HEAD\n# Frontend\n", "# Frontend\n")
c = c.replace("=======\ndata/cs231n/\n>>>>>>> main\n", "data/cs231n/\n")
with open(".gitignore", "w") as f: f.write(c)

with open("Dockerfile", "r") as f:
    c = f.read()
c = c.replace("<<<<<<< HEAD\n# Copy installed deps from builder\nCOPY --from=builder /build/deps /app/deps\n=======\n# Copy project configuration files\nCOPY pyproject.toml uv.lock* ./\n>>>>>>> main\n", 
"""# Copy project configuration files and deps
COPY pyproject.toml uv.lock* ./
COPY --from=builder /build/deps /app/deps
""")
with open("Dockerfile", "w") as f: f.write(c)

with open("docker-compose.yml", "r") as f:
    c = f.read()
# For docker-compose, luan_update replaced it completely but let's just keep HEAD's version since it has db, redis, frontend.
# Wait, I'll just git checkout --ours docker-compose.yml

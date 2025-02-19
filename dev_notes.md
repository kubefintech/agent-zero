
# Fix Local Run Error
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

# Run Agent
```bash
docker run -d --name agent_zero -p 50080:80 -v $(pwd):/a0 frdel/agent-zero-run  
```



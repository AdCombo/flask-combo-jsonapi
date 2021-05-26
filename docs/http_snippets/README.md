# Generate HTTP code snippets


## Install

```shell
# to use in cli
npm install --global httpsnippet
```

```shell
# to use as a module
npm install --save httpsnippet
```

## Generate

### Create all snippets and run requests for them

```shell
# run and create for all
./run_and_create.sh
```

### Or do it manually:

```shell
# example
httpsnippet example.json --target node --client unirest --output ./snippets
```

```shell
# minimal api to python3
httpsnippet minimal_api__create_person.json --target python --client python3 --output ./snippets
```

```shell
# minimal api to http
httpsnippet minimal_api__create_person.json --target http --output ./snippets
```


```shell
# process multiple
httpsnippet ./*.json --target http --output ./snippets
```


### Create requests and run them, write results 

```shell
# create python-requests requests snippets
httpsnippet ./*.json --target python --client requests --output ./snippets
```

```shell
# Run requests, save output
python3 update_snippets_with_responses.py
```

> **Pro tip:** run webserver for specs before running update_snippets_with_responses, otherwise it won't work 😉 


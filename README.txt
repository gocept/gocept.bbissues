================================
The gocept.bbissues distribution
================================

Collect open issues from multiple bitbucket repositories and generate a nice html page.

This package is compatible with Python version 2.7.

You have to provide a config file with the following content:

```
[config]
log = issues.log
# optional
template_path = template.jj2

[bitbucket]
projects = owner:project1
    owner:project2
```


The template will be rendered using jinja2, and could have the following content:


```
{% for project in projects %}

<h2>{{project.name}}</h2>

{% for issue in project.issues %}

<h3>{{issue.title}}</h3>
 <pre>
 {{issue.title}}
 {{issue.content}}
 {{issue.status}}
 {{issue.created}}
 {{issue.priority}}
 {{issue.url}}
 {{issue.author}}
 </pre>

{% endfor %}

{% endfor %}
```

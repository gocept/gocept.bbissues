import requests
from jinja2 import Template
import ConfigParser
import logging
import dateutil.parser
import pkg_resources
import argparse



log = logging.getLogger('bbissues')


parser = argparse.ArgumentParser(
    description='Collect issues from bitbucket issue trackers.')
parser.add_argument('--config', dest='config_path', help='Config file.',
    required=True)


BB_ISSUES_BASE_URL = 'https://api.bitbucket.org/1.0/repositories/{}/{}/issues?status=!resolved'
BB_PULLREQUESTS_BASE_URL = 'https://api.bitbucket.org/2.0/repositories/{}/{}/pullrequests'

BB_WEB_BASE_URL = 'https://bitbucket.org/{}'
DEFAULT_TEMPLATE = pkg_resources.resource_string('gocept.bbissues', 'index.jj2')

def timefmt(timestr):
    return dateutil.parser.parse(timestr).strftime('%Y-%m-%d %H:%M')



def get_bb_json(urltemplate, spec):
    owner, project = spec.split(':')
    url = urltemplate.format(owner, project)
    result = requests.get(url)
    if not result.ok:
        error = result.json()['error']['message']
        log.warn('Error while calling {}: {}'.format(url, error))
        return
    return result.json()

def parse_spec(spec):
    return spec.split(':')

def collect_project_pullrequests(spec):
    owner, project = parse_spec(spec)
    prs = get_bb_json(BB_PULLREQUESTS_BASE_URL, spec)
    data = []
    if prs is None:
        return
    for pr in prs['values']:
        if pr['state'] != 'OPEN':
            continue
        prdata = dict(
            title=pr['title'],
            content=pr['description'].strip(),
            status=pr['state'],
            created=timefmt(pr['created_on']),
            priority='pullrequest',
            prioclass=prioclass('normal'),
            url=BB_WEB_BASE_URL.format(
                '{}/{}/pull-requests/{}'.format(owner, project, pr['id'])),
            author=pr['author']['display_name'])
        data.append(prdata)
    return data


def prioclass(prio):
    return dict(minor='warning',
                major='danger',
                normal='primary').get(prio, 'default')


def collect_project_issues(spec):
    owner, project = spec.split(':')
    issues = get_bb_json(BB_ISSUES_BASE_URL, spec)
    if issues is None:
        return
    data = []
    for issue in issues['issues']:
        issuedata = dict(
            title=issue['title'],
            content=issue['content'].strip(),
            status=issue['status'],
            created=timefmt(issue['created_on']),
            priority=issue['priority'],
            prioclass=prioclass(issue['priority']),
            url=BB_WEB_BASE_URL.format(issue['resource_uri'][18:]),
            author=issue['reported_by']['display_name'])
        data.append(issuedata)
    return data


def main():
    args = parser.parse_args()
    config = ConfigParser.ConfigParser()
    config.read(args.config_path)
    try:
        custom_template = config.get('config', 'template_path')
        with open(custom_template) as templatefile:
            template_content = templatefile.read()
    except ConfigParser.NoOptionError:
        template_content = DEFAULT_TEMPLATE
    template = Template(template_content)
    logging.basicConfig(
        filename=config.get('config', 'log'), level=logging.WARNING)
    projects = config.get('bitbucket', 'projects')
    projectsdata = []
    for project in projects.split():
        issuedata = collect_project_issues(project)
        prdata = collect_project_pullrequests(project)
        if issuedata or prdata:
            projectsdata.append(
                dict(name=parse_spec(project)[1], issues=issuedata, pullrequests=prdata))

    result = template.render(projects=projectsdata)
    print result


if __name__ == '__main__':
    main()

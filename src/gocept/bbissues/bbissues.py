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

DEFAULT_TEMPLATE = pkg_resources.resource_string(
    'gocept.bbissues', 'index.jj2')


def timefmt(timestr):
    return dateutil.parser.parse(timestr).strftime('%Y-%m-%d %H:%M')


class Bitbucket(object):

    issue_base_url = ('https://api.bitbucket.org/1.0/repositories/{}/{}/'
                      'issues?status=!resolved')
    pullrequest_base_url = ('https://api.bitbucket.org/2.0/repositories/{}/{}'
                            '/pullrequests')
    web_base_url = 'https://bitbucket.org/{}'

    def __init__(self, projects):
        self.projects = projects

    def get_bb_json(self, urltemplate, spec):
        owner, project = spec.split(':')
        url = urltemplate.format(owner, project)
        try:
            result = requests.get(url)
            if not result.ok:
                error = result.json()['error']['message']
                log.warn('Error while calling {}: {}'.format(url, error))
                return
        except requests.ConnectionError:
            log.warn('Connection error while calling {}'.format(url))
            return
        return result.json()

    def parse_spec(self, spec):
        return spec.split(':')

    def collect_project_pullrequests(self, spec):
        owner, project = self.parse_spec(spec)
        prs = self.get_bb_json(self.pullrequest_base_url, spec)
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
                prioclass=self.prioclass('normal'),
                url=self.web_base_url.format(
                    '{}/{}/pull-requests/{}'.format(owner, project, pr['id'])),
                author=pr['author']['display_name'])
            data.append(prdata)
        return data

    def prioclass(self, prio):
        return dict(minor='warning',
                    major='danger',
                    normal='primary').get(prio, 'default')

    def collect_project_issues(self, spec):
        owner, project = spec.split(':')
        issues = self.get_bb_json(self.issue_base_url, spec)
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
                prioclass=self.prioclass(issue['priority']),
                url=self.web_base_url.format(issue['resource_uri'][18:]),
                author=issue['reported_by']['display_name'])
            data.append(issuedata)
        return data

    def __call__(self):
        for project in self.projects:
            issuedata = self.collect_project_issues(project)
            prdata = self.collect_project_pullrequests(project)
            if issuedata or prdata:
                yield dict(
                    name=self.parse_spec(project)[1],
                    issues=issuedata,
                    pullrequests=prdata)


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
    projectsdata = Bitbucket(projects.split())()

    result = template.render(projects=projectsdata)
    print result


if __name__ == '__main__':
    main()

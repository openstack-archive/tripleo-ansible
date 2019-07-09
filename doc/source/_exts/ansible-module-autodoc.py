# Copyright 2019 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import imp
import os

from docutils import core
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers import rst
from docutils.writers.html4css1 import Writer

from sphinx import addnodes

import yaml


class AnsibleAutoPluginDirective(Directive):
    directive_name = "ansibleautoplugin"
    has_content = True
    option_spec = {
        'module': rst.directives.unchanged_required,
        'documentation': rst.directives.unchanged,
        'examples': rst.directives.unchanged
    }

    @staticmethod
    def _render_html(source):
        return core.publish_parts(
            source=source,
            writer=Writer(),
            writer_name='html',
            settings_overrides={'no_system_messages': True}
        )

    def make_node(self, title, contents, content_type=None):
        section = nodes.section(
            title,
            nodes.title(text=title),
            ids=[nodes.make_id(__file__)],
        )

        if not content_type:
            # Doc section
            for content in contents['docs']:
                for paragraph in content.split('\n'):
                    retnode = nodes.paragraph()
                    html = self._render_html(source=paragraph)
                    retnode += nodes.raw('', html['body'], format='html')
                    section.append(retnode)

            # Options Section
            options_list = nodes.field_list()
            options_section = nodes.section(
                'Options',
                nodes.title(text='Options'),
                ids=[nodes.make_id(__file__)],
            )
            for key, value in contents['options'].items():
                body = nodes.field_body()
                if isinstance(value['description'], list):
                    for desc in value['description']:
                        html = self._render_html(source=desc)
                        body.append(
                            nodes.raw('', html['body'], format='html')
                        )
                else:
                    html = self._render_html(source=value['description'])
                    body.append(
                        nodes.raw('', html['body'], format='html')
                    )

                field = nodes.field()
                field.append(nodes.field_name(text=key))
                field.append(body)
                options_list.append(field)
            else:
                options_section.append(options_list)
                section.append(options_section)

            # Authors Section
            authors_list = nodes.field_list()
            authors_section = nodes.section(
                'Authors',
                nodes.title(text='Authors'),
                ids=[nodes.make_id(__file__)],
            )
            field = nodes.field()
            field.append(nodes.field_name(text=''))
            for author in contents['author']:
                body = nodes.field_body()
                html = self._render_html(source=author)
                body.append(
                    nodes.raw('', html['body'], format='html')
                )
                field.append(body)
            else:
                authors_list.append(field)
                authors_section.append(authors_list)
                section.append(authors_section)

        elif content_type == 'yaml':
            for content in contents:
                retnode = nodes.literal_block(text=content)
                retnode['language'] = 'yaml'
                section.append(retnode)

        return section

    def load_module(self, filename):
        return imp.load_source('__ansible_module__', filename)

    def build_documentation(self, module):
        docs = yaml.safe_load(module.DOCUMENTATION)
        doc_data = dict()
        doc_data['docs'] = docs['description']
        doc_data['author'] = docs.get('author', list())
        doc_data['options'] = docs.get('options', dict())
        return doc_data

    def build_examples(self, module):
        examples = yaml.safe_load(module.EXAMPLES)
        return_examples = list()
        for example in examples:
            return_examples.append(
                yaml.safe_dump([example], default_flow_style=False)
            )
        return return_examples

    def run(self):
        module = self.load_module(filename=self.options['module'])
        return_data = list()
        if self.options.get('documentation'):
            docs = self.build_documentation(module=module)
            return_data.append(
                self.make_node(
                    title="Module Documentation",
                    contents=docs
                )
            )

        if self.options.get('examples'):
            examples = self.build_examples(module=module)
            return_data.append(
                self.make_node(
                    title="Example Tasks",
                    contents=examples,
                    content_type='yaml'
                )
            )

        return return_data


def setup(app):
    classes = [
        AnsibleAutoPluginDirective,
    ]
    for directive_class in classes:
        app.add_directive(directive_class.directive_name, directive_class)

    return {'version': '0.1'}

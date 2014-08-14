import requests
import json

API_URL = 'http://api.scb.se/OV0104/v1/doris/sv/ssd/'

class Explorer:
    cache = {}
    def __init__(self, path, data):
        self.data = data
        self.path = path
    
    def get_attributes(self):
        raise NotImplementedError()
    def get_attribute(self, name):
        raise NotImplementedError()
        
    def __dir__(self):
        categories = []
        for attr in self.get_attributes():
            categories.append(attr)
        return categories
        
    def __getattr__(self, name):
        if name in self.cache:
            return self.cache[name]
        for attr in self.get_attributes():
            if name == attr:
                self.cache[name] = self.get_attribute(name)
                return self.cache[name]

class ListExplorer(Explorer):    
        
    def get_attributes(self):
        attrs = []
        for item in self.data:
            attrs.append(item['id'])
        return attrs
    
    def get_attribute(self, name):
        return ExplorerFactory.create(self.path + name + '/')

    
    def _repr_html_(self):
        html = '<table>'
        html += '<tr><th>id</th><th>Description</th></tr>'
        for item in self.data:
            html += '<tr><td>%s</td><td>%s</td></tr>' % (item['id'], item['text'])
        html += '</table>'
        return html
    
class Variable:
    def __init__(self, code, text, values, valueDescriptions, max_rows=20):
        self.code = code
        self.text = text
        self.values = values
        self.valueDescriptions = valueDescriptions
        self.max_rows=max_rows

    def all_rows(self):
        return Variable(self.code, self.text, self.values, self.valueDescriptions, max_rows=100000)


    def lookup(self, value):
        if value in self.values:
            return self.valueDescriptions[self.values.index(value)]

    def reverse_lookup(self, description):
        if description in self.valueDescriptions:
            return self.values[self.valueDescriptions.index(description)]

    def _repr_html_(self):
        html = '<h3>%s</h3>' % self.code
        html += '<table>'
        html += '<tr><th>Value</th><th>Text</th></tr>'
        num_items = len(self.values)
        if num_items <= self.max_rows:
            for i in xrange(num_items):
                html += '<tr><td>%s</td><td>%s</td></tr>' % (self.values[i], self.valueDescriptions[i])
        else:
            for i in xrange(10):
                html += '<tr><td>%s</td><td>%s</td></tr>' % (self.values[i], self.valueDescriptions[i])
            html += '<td colspan=2>%d more rows</p>' % (num_items - 20,)
            for i in xrange(num_items -10, num_items):
                html += '<tr><td>%s</td><td>%s</td></tr>' % (self.values[i], self.valueDescriptions[i])
        html += '</table>'
        return html

class MetadataExplorer(Explorer):        

    def get_attributes(self):
        return [var['code'] for var in self.data['variables']]

    def get_attribute(self, name):
        for variable in self.data['variables']:
            if variable['code'] == name:
                return Variable(
                            code=name,
                            text=variable['text'],
                            values=variable['values'], valueDescriptions=variable['valueTexts']
                )

    def _repr_html_(self):
        html = '<h2>%s</h2>' % self.data['title']
        html += '<p>Variables</p>'
        html += '<table>'
        html += '<tr>'
        for attr in self.get_attributes():
            html += '<td style="vertical-align:top">'
            var = self.get_attribute(attr)
            html += var._repr_html_()
            html += '</td>'
        html += '</tr></table>'
        return html
    
    def query(self, **kwargs):
        query = []
        for key, value in kwargs.iteritems():
            if isinstance(value, basestring):
                value = [value]
            q = {
                'code': key,
                'selection': {
                    'filter': 'item',
                    'values': value
                }
            }
            query.append(q)

        request = {'query':query, 'response':{'format':'json'}}
        r = requests.post(self.path, data=json.dumps(request))
        data = json.loads(r.text.strip(u'\ufeff'))
        return Result(data, query=json.dumps(request))


class Result:

    def __init__(self, data, query):
        self.query = query
        self.raw_data = data
        self.columns = [col['text'] for col in self.raw_data['columns']]
        self.data = []
        for data_row in self.raw_data['data']:
            row = []
            for col in data_row['key']:
                row.append(col)
            for col in data_row['values']:
                try:
                    col = float(col)
                except:
                    pass
                row.append(col)
            self.data.append(row)

    def _repr_html_(self):
        html = '<table>'
        html += '<tr>'
        for col in self.columns:
            html += '<th>%s</th>' % col
        html += '</tr>'
        for row in self.data:
            html += '<tr>'
            for col in row:
                if isinstance(col, unicode):
                    value = col
                else:
                    value = unicode(col)
                html += '<td>%s</td>' % value
            html += '</tr>'
        html += '</table>'
        return html


class ExplorerFactory:

    @classmethod
    def create(cls, path):
        r = requests.get(path)
        data = r.json()
        if 'variables' in data:
            return MetadataExplorer(path, data)
        else:
            return ListExplorer(path, data)


def get_client():
    return ExplorerFactory.create(API_URL)


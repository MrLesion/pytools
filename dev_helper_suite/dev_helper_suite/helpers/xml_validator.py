"""Check XML well-formedness with exact parser line/column diagnostics."""
from xml.parsers import expat
from common import main, report, issue
from document_input import document_input


def run(params):
    """Validate XML structure; DTDs/entities and XSD validation are not supported."""
    payload, source = document_input(params)
    parser = expat.ParserCreate(namespace_separator='}')
    data = {'source': source, 'root_element': None, 'elements': 0, 'attributes': 0, 'max_depth': 0,
            'validation': 'XML well-formedness; no XSD/DTD validation'}
    depth = 0

    def start(name, attrs):
        nonlocal depth
        depth += 1
        if depth > 256:
            raise ValueError('XML exceeds supported nesting depth (256).')
        if data['root_element'] is None:
            data['root_element'] = name
        data['elements'] += 1
        data['attributes'] += len(attrs)
        data['max_depth'] = max(depth, data['max_depth'])

    def end(name):
        nonlocal depth
        depth -= 1

    def forbid(*args):
        raise ValueError('DTDs and entity declarations are not supported.')

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = forbid
    parser.EntityDeclHandler = forbid
    parser.ExternalEntityRefHandler = forbid
    try:
        parser.Parse(payload, True)
    except (expat.ExpatError, ValueError) as exc:
        line = getattr(exc, 'lineno', parser.CurrentLineNumber)
        column = getattr(exc, 'offset', parser.CurrentColumnNumber) + 1
        data.update(line=line, column=column)
        return report('Invalid or unsupported XML', [issue(str(exc), f'{source}: line {line}, column {column}')], data)
    return report('Valid XML', data=data)


if __name__ == '__main__':
    raise SystemExit(main(run))

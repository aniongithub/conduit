from typing import Generator, Iterator, Dict, Any, Optional, Union
from dataclasses import dataclass
from ..pipelineElement import PipelineElement
from ..template_renderer import get_template_renderer
import urllib.request
import urllib.parse
import json
import ssl

@dataclass
class RestApiInput:
    """Input specification for RestApi element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    body: Optional[str] = None  # Raw request body (JSON string, form data, etc.)
    timeout: Optional[int] = None
    verify_ssl: Optional[bool] = None
    response_format: Optional[str] = None
    output_template: Optional[str] = None

class RestApi(PipelineElement):
    """
    REST API pipeline element for making HTTP requests.
    
    Supports GET, POST, PUT, DELETE, PATCH methods with full configuration
    for headers, query parameters, form data, JSON payloads, and authentication.
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
        response_format: str = "json",  # json, text, binary
        output_template: Optional[str] = None
    ):
        """
        Initialize REST API element.
        
        Args:
            url: Default URL for requests (can be overridden per-datum)
            method: Default HTTP method (can be overridden per-datum)
            headers: Default headers (can be overridden per-datum)
            query_params: Default query parameters (can be overridden per-datum)
            body: Default request body (can be overridden per-datum)
            timeout: Default request timeout in seconds
            verify_ssl: Default SSL verification setting
            response_format: Default response parsing format (json, text, binary)
            output_template: Default Jinja2 template for formatting output
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[RestApiInput]) -> Generator[Any, None, None]:
        """Process each input item by making REST API calls."""
        renderer = get_template_renderer()
        
        for request in input:
            # Apply constructor defaults to None fields
            request = self.apply_defaults(request)
            
            # Validate response format
            if request.response_format.lower() not in ['json', 'text', 'binary']:
                raise ValueError(f"Unsupported response format: {request.response_format}")
            
            try:
                # URL is required (either from constructor or per-datum)
                if request.url is None:
                    raise ValueError("URL is required (either from constructor or per-datum)")
                
                # Create context for template rendering
                context = {"input": request}
                
                # Render URL template
                rendered_url = renderer.render_template(request.url, context)
                
                # Render query parameters
                rendered_query_params = {}
                if request.query_params:
                    for key, value in request.query_params.items():
                        rendered_query_params[key] = renderer.render_template(str(value), context)
                
                # Add query parameters to URL
                if rendered_query_params:
                    url_parts = urllib.parse.urlparse(rendered_url)
                    query = urllib.parse.parse_qs(url_parts.query)
                    query.update(rendered_query_params)
                    encoded_query = urllib.parse.urlencode(query, doseq=True)
                    rendered_url = urllib.parse.urlunparse(
                        url_parts._replace(query=encoded_query)
                    )
                
                # Prepare headers
                request_headers = {}
                if request.headers:
                    for key, value in request.headers.items():
                        request_headers[key] = renderer.render_template(str(value), context)
                
                # Prepare request data
                request_data = None
                method = request.method.upper()
                
                # Validate method
                if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Handle request body if provided
                if request.body and method in ['POST', 'PUT', 'PATCH']:
                    # Render body template
                    rendered_body = renderer.render_template(request.body, context)
                    request_data = rendered_body.encode('utf-8')
                    
                    # Set Content-Type if not already specified
                    if 'Content-Type' not in request_headers and 'content-type' not in request_headers:
                        # Try to detect content type from body format
                        try:
                            json.loads(rendered_body)
                            request_headers['Content-Type'] = 'application/json'
                        except json.JSONDecodeError:
                            # Default to form data if not valid JSON
                            request_headers['Content-Type'] = 'application/x-www-form-urlencoded'
                
                # Create request
                http_request = urllib.request.Request(
                    rendered_url,
                    data=request_data,
                    headers=request_headers,
                    method=method
                )
                
                # Configure SSL context
                ssl_context = None
                if not request.verify_ssl:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                
                # Make the request
                try:
                    with urllib.request.urlopen(http_request, timeout=request.timeout, context=ssl_context) as response:
                        # Read response
                        response_data = response.read()
                        
                        # Parse response based on format
                        if request.response_format.lower() == 'json':
                            try:
                                parsed_response = json.loads(response_data.decode('utf-8'))
                            except json.JSONDecodeError:
                                parsed_response = {
                                    'error': 'Invalid JSON response',
                                    'raw_response': response_data.decode('utf-8', errors='replace')
                                }
                        elif request.response_format.lower() == 'text':
                            parsed_response = response_data.decode('utf-8')
                        else:  # binary
                            parsed_response = response_data
                        
                        # Add response metadata
                        if isinstance(parsed_response, dict):
                            parsed_response['_metadata'] = {
                                'status_code': response.status,
                                'headers': dict(response.headers),
                                'url': response.url
                            }
                        else:
                            # For non-dict responses, wrap in a dict with metadata
                            result_dict = {
                                'data': parsed_response,
                                '_metadata': {
                                    'status_code': response.status,
                                    'headers': dict(response.headers),
                                    'url': response.url
                                }
                            }
                            parsed_response = result_dict
                        
                        # Apply output template if provided
                        if request.output_template:
                            template_context = {
                                'response': parsed_response,
                                'input': request,
                                'status_code': parsed_response.get('_metadata', {}).get('status_code'),
                                'headers': parsed_response.get('_metadata', {}).get('headers', {})
                            }
                            result = renderer.render_template(request.output_template, template_context)
                        else:
                            result = parsed_response
                        
                        yield result
                
                except urllib.error.HTTPError as e:
                    # Handle HTTP errors (4xx, 5xx)
                    error_response = {
                        'error': f'HTTP {e.code}: {e.reason}',
                        'status_code': e.code,
                        'url': rendered_url,
                        'input': request
                    }
                    
                    # Try to read error response body
                    try:
                        error_body = e.read().decode('utf-8')
                        if request.response_format.lower() == 'json':
                            try:
                                error_response['error_details'] = json.loads(error_body)
                            except json.JSONDecodeError:
                                error_response['error_details'] = error_body
                        else:
                            error_response['error_details'] = error_body
                    except:
                        pass
                    
                    yield error_response
                
                except urllib.error.URLError as e:
                    # Handle connection errors
                    yield {
                        'error': f'Connection error: {str(e.reason)}',
                        'url': rendered_url,
                        'input': request
                    }
                
                except Exception as e:
                    # Handle other errors
                    yield {
                        'error': f'Request failed: {str(e)}',
                        'url': rendered_url,
                        'input': request
                    }
            
            except Exception as e:
                # Handle template rendering or other setup errors
                yield {
                    'error': f'Request setup failed: {str(e)}',
                    'input': request
                }
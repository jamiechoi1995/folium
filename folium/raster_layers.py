# -*- coding: utf-8 -*-

"""
Wraps leaflet TileLayer, WmsTileLayer (TileLayer.WMS), ImageOverlay, and VideoOverlay

"""

from __future__ import (absolute_import, division, print_function)

import json

from branca.element import Element, Figure

from folium.map import Layer
from folium.utilities import _parse_wms, image_to_url, mercator_transform

from jinja2 import Environment, PackageLoader, Template

from six import binary_type, text_type


ENV = Environment(loader=PackageLoader('folium', 'templates'))


class TileLayer(Layer):
    """Create a tile layer to append on a Map.

    Parameters
    ----------
    tiles: str, default 'OpenStreetMap'
        Map tileset to use. Can choose from this list of built-in tiles:
            - "OpenStreetMap"
            - "Mapbox Bright" (Limited levels of zoom for free tiles)
            - "Mapbox Control Room" (Limited levels of zoom for free tiles)
            - "Stamen" (Terrain, Toner, and Watercolor)
            - "Cloudmade" (Must pass API key)
            - "Mapbox" (Must pass API key)
            - "CartoDB" (positron and dark_matter)

        You can pass a custom tileset to Folium by passing a Leaflet-style
        URL to the tiles parameter: ``http://{s}.yourtiles.com/{z}/{x}/{y}.png``
    min_zoom: int, default 1
        Minimal zoom for which the layer will be displayed.
    max_zoom: int, default 18
        Maximal zoom for which the layer will be displayed.
    attr: string, default None
        Map tile attribution; only required if passing custom tile URL.
    API_key: str, default None
        API key for Cloudmade or Mapbox tiles.
    detect_retina: bool, default False
        If true and user is on a retina display, it will request four
        tiles of half the specified size and a bigger zoom level in place
        of one to utilize the high resolution.
    name : string, default None
        The name of the Layer, as it will appear in LayerControls
    overlay : bool, default False
        Adds the layer as an optional overlay (True) or the base layer (False).
    control : bool, default True
        Whether the Layer will be included in LayerControls.
    subdomains: list of strings, default ['abc']
        Subdomains of the tile service.
    """
    def __init__(self, tiles='OpenStreetMap', min_zoom=1, max_zoom=18,
                 attr=None, API_key=None, detect_retina=False,
                 name=None, overlay=False,
                 control=True, no_wrap=False, subdomains='abc'):
        self.tile_name = (name if name is not None else
                          ''.join(tiles.lower().strip().split()))
        super(TileLayer, self).__init__(name=self.tile_name, overlay=overlay,
                                        control=control)
        self._name = 'TileLayer'
        self._env = ENV

        options = {
            'minZoom': min_zoom,
            'maxZoom': max_zoom,
            'noWrap': no_wrap,
            'attribution': attr,
            'subdomains': subdomains,
            'detectRetina': detect_retina,
        }
        self.options = json.dumps(options, sort_keys=True, indent=2)

        self.tiles = ''.join(tiles.lower().strip().split())
        if self.tiles in ('cloudmade', 'mapbox') and not API_key:
            raise ValueError('You must pass an API key if using Cloudmade'
                             ' or non-default Mapbox tiles.')
        templates = list(self._env.list_templates(
            filter_func=lambda x: x.startswith('tiles/')))
        tile_template = 'tiles/'+self.tiles+'/tiles.txt'
        attr_template = 'tiles/'+self.tiles+'/attr.txt'

        if tile_template in templates and attr_template in templates:
            self.tiles = self._env.get_template(tile_template).render(API_key=API_key)  # noqa
            self.attr = self._env.get_template(attr_template).render()
        else:
            self.tiles = tiles
            if not attr:
                raise ValueError('Custom tiles must'
                                 ' also be passed an attribution.')
            if isinstance(attr, binary_type):
                attr = text_type(attr, 'utf8')
            self.attr = attr

        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            var {{this.get_name()}} = L.tileLayer(
                '{{this.tiles}}',
                {{ this.options }}
                ).addTo({{this._parent.get_name()}});
        {% endmacro %}
        """)  # noqa


class WmsTileLayer(Layer):
    """
    Creates a Web Map Service (WMS) layer.

    Parameters
    ----------
    url : str
        The url of the WMS server.
    name : string, default None
        The name of the Layer, as it will appear in LayerControls
    layers : str, default ''
        The names of the layers to be displayed.
    styles : str, default ''
        Comma-separated list of WMS styles.
    fmt : str, default 'image/jpeg'
        The format of the service output.
        Ex: 'image/png'
    transparent: bool, default False
        Whether the layer shall allow transparency.
    version : str, default '1.1.1'
        Version of the WMS service to use.
    attr : str, default None
        The attribution of the service.
        Will be displayed in the bottom right corner.
    overlay : bool, default True
        Adds the layer as an optional overlay (True) or the base layer (False).
    control : bool, default True
        Whether the Layer will be included in LayerControls
    **kwargs : additional keyword arguments
        Passed through to the underlying tileLayer.wms object and can be used
        for setting extra tileLayer.wms parameters or as extra parameters in
        the WMS request.

    For more information see:
    http://leafletjs.com/reference.html#tilelayer-wms

    """
    def __init__(self, url, name=None, attr='', overlay=True, control=True, **kwargs):  # noqa
        super(WmsTileLayer, self).__init__(overlay=overlay, control=control, name=name)  # noqa
        self.url = url
        # Options.
        options = _parse_wms(**kwargs)
        options.update({'attribution': attr})

        self.options = json.dumps(options, sort_keys=True, indent=2)

        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            var {{this.get_name()}} = L.tileLayer.wms(
                '{{ this.url }}',
                {{ this.options }}
                ).addTo({{this._parent.get_name()}});

        {% endmacro %}
        """)  # noqa


class ImageOverlay(Layer):
    """
    Used to load and display a single image over specific bounds of
    the map, implements ILayer interface.

    Parameters
    ----------
    image: string, file or array-like object
        The data you want to draw on the map.
        * If string, it will be written directly in the output file.
        * If file, it's content will be converted as embedded in the output file.
        * If array-like, it will be converted to PNG base64 string and embedded in the output.
    bounds: list
        Image bounds on the map in the form [[lat_min, lon_min],
        [lat_max, lon_max]]
    opacity: float, default Leaflet's default (1.0)
    alt: string, default Leaflet's default ('')
    origin: ['upper' | 'lower'], optional, default 'upper'
        Place the [0,0] index of the array in the upper left or
        lower left corner of the axes.
    colormap: callable, used only for `mono` image.
        Function of the form [x -> (r,g,b)] or [x -> (r,g,b,a)]
        for transforming a mono image into RGB.
        It must output iterables of length 3 or 4,
        with values between 0 and 1.
        Hint: you can use colormaps from `matplotlib.cm`.
    mercator_project: bool, default False.
        Used only for array-like image.  Transforms the data to
        project (longitude, latitude) coordinates to the
        Mercator projection.
        Beware that this will only work if `image` is an array-like
        object.
    pixelated: bool, default True
        Sharp sharp/crips (True) or aliased corners (False).

    See http://leafletjs.com/reference-1.2.0.html#imageoverlay for more
    options.

    """
    def __init__(self, image, bounds, origin='upper', colormap=None,
                 mercator_project=False, overlay=True, control=True,
                 pixelated=True, name=None, **kwargs):
        super(ImageOverlay, self).__init__(overlay=overlay, control=control, name=name)  # noqa

        options = {
            'opacity': kwargs.pop('opacity', 1.),
            'alt': kwargs.pop('alt', ''),
            'interactive': kwargs.pop('interactive', False),
            'crossOrigin': kwargs.pop('cross_origin', False),
            'errorOverlayUrl': kwargs.pop('error_overlay_url', ''),
            'zIndex': kwargs.pop('zindex', 1),
            'className': kwargs.pop('class_name', ''),
        }
        self._name = 'ImageOverlay'
        self.pixelated = pixelated

        if mercator_project:
            image = mercator_transform(
                image,
                [bounds[0][0],
                 bounds[1][0]],
                origin=origin)

        self.url = image_to_url(image, origin=origin, colormap=colormap)

        self.bounds = json.loads(json.dumps(bounds))
        self.options = json.dumps(options, sort_keys=True, indent=2)
        self._template = Template(u"""
            {% macro script(this, kwargs) %}
                var {{this.get_name()}} = L.imageOverlay(
                    '{{ this.url }}',
                    {{ this.bounds }},
                    {{ this.options }}
                    ).addTo({{this._parent.get_name()}});
            {% endmacro %}
            """)

    def render(self, **kwargs):
        super(ImageOverlay, self).render()

        figure = self.get_root()
        assert isinstance(figure, Figure), ('You cannot render this Element '
                                            'if it is not in a Figure.')
        pixelated = """<style>
        .leaflet-image-layer {
        image-rendering: -webkit-optimize-contrast; /* old android/safari*/
        image-rendering: crisp-edges; /* safari */
        image-rendering: pixelated; /* chrome */
        image-rendering: -moz-crisp-edges; /* firefox */
        image-rendering: -o-crisp-edges; /* opera */
        -ms-interpolation-mode: nearest-neighbor; /* ie */
        }
        </style>"""

        if self.pixelated:
            figure.header.add_child(Element(pixelated), name='leaflet-image-layer')  # noqa

    def _get_self_bounds(self):
        """
        Computes the bounds of the object itself (not including it's children)
        in the form [[lat_min, lon_min], [lat_max, lon_max]].

        """
        return self.bounds


class VideoOverlay(Layer):
    """
    Used to load and display a video over the map.

    Parameters
    ----------
    video_url: URL of the video
    bounds: list
        Video bounds on the map in the form [[lat_min, lon_min],
        [lat_max, lon_max]]
    opacity: float, default Leaflet's default (1.0)
    attr: string, default Leaflet's default ('')

    """
    def __init__(self, video_url, bounds, opacity=1., attr=None,
                 autoplay=True, loop=True):
        super(VideoOverlay, self).__init__()
        self._name = 'VideoOverlay'

        self.video_url = video_url

        self.bounds = json.loads(json.dumps(bounds))
        options = {
            'opacity': opacity,
            'attribution': attr,
            'loop': loop,
            'autoplay': autoplay,
        }
        self.options = json.dumps(options)

        self._template = Template(u"""
            {% macro script(this, kwargs) %}
                var {{this.get_name()}} = L.videoOverlay(
                    '{{ this.video_url }}',
                    {{ this.bounds }},
                    {{ this.options }}
                    ).addTo({{this._parent.get_name()}});
            {% endmacro %}
            """)

    def _get_self_bounds(self):
        """
        Computes the bounds of the object itself (not including it's children)
        in the form [[lat_min, lon_min], [lat_max, lon_max]]

        """
        return self.bounds
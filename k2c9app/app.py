import matplotlib
matplotlib.use('Agg')

import flask
from flask import Flask, request
from astropy.coordinates import SkyCoord

try:
    from io import BytesIO  # Python 3
except ImportError:
    from cStringIO import StringIO as BytesIO  # Legacy Python

from K2fov import c9


c9app = Flask('k2c9app', static_url_path='')


def _parse_single_pos(pos):
    try:
        pos_crd = SkyCoord(pos)
    except ValueError:  # The coordinate string is ambiguous
        if ":" in pos:
            pos_crd = SkyCoord(pos, unit="hour,deg")
        else:
            pos_crd = SkyCoord(pos, unit="deg")
    return pos_crd


def _parse_pos(pos):
    """Parses the 'pos' argument.

    Returns
    -------
    positions : list of `astropy.coordinates.SkyCoord` objects
    """
    if pos is None:
        return []
    positions = [_parse_single_pos(single_pos)
                   for single_pos in pos.split(",")]
    return positions


def _in_region(pos):
    """Returns a list of booleans."""
    positions = _parse_pos(pos)
    return [c9.inMicrolensRegion(poscrd.ra.deg, poscrd.dec.deg)
            for poscrd in positions]


@c9app.route('/')
def root():
    return c9app.send_static_file('index.html')


@c9app.route('/demo')
def demo():
    return flask.redirect("check-visibility?pos=270.0 -28.0,270.5 -28.2")


@c9app.route('/in-microlens-region')
def in_microlens_region():
    pos = request.args.get('pos', default=None, type=str)
    fmt = request.args.get('fmt', default=None, type=str)
    input_strings = pos.split(",")
    result = _in_region(pos)
    if fmt == "csv":
        csv = "position,in_region\r\n"
        for idx in range(len(result)):
            csv += input_strings[idx]
            if result[idx]:
                csv += ",yes\r\n"
            else:
                csv += ",no\r\n"
    else:
        csv = ""
        for idx in range(len(result)):
            if result[idx]:
                csv += "yes\r\n"
            else:
                csv += "no\r\n"
    return flask.Response(csv, mimetype='text/plain')


@c9app.route('/check-visibility')
def check_visibility():
    pos = request.args.get('pos', default=None, type=str)
    try:
        positions = _parse_pos(pos)
    except Exception:
        return "Error: the input is invalid."
    pos_hmsdms = [poscrd.to_string("hmsdms") for poscrd in positions]
    pos_decimal = [poscrd.to_string("decimal") for poscrd in positions]
    return flask.render_template('check-visibility.html',
                                 pos=pos,
                                 pos_split=pos.split(","),
                                 positions=positions,
                                 pos_hmsdms=pos_hmsdms,
                                 pos_decimal=pos_decimal,
                                 in_region=_in_region(pos))


@c9app.route('/k2c9.png')
def k2c9_png():
    # The user may optionally mark a position
    pos = request.args.get('pos', default=None, type=str)
    size = request.args.get('size', default=None, type=float)

    positions = _parse_pos(pos)
    # Create the plot
    fovplot = c9.C9FootprintPlot()
    superstamp_patches, channel_patches = fovplot.plot_outline()
    fovplot.fig.tight_layout()
    if len(positions) > 0:
        ra = [poscrd.ra.deg for poscrd in positions]
        dec = [poscrd.dec.deg for poscrd in positions]
        user_position = fovplot.ax.scatter(ra, dec,
                                           marker='+', lw=2.5, s=200,
                                           zorder=900, color="k")
        legend_objects = (user_position, superstamp_patches[0][0])
        legend_labels = ("Your position", "K2C9 Observations")
    else:
        legend_objects = (superstamp_patches[0][0],)
        legend_labels = ("K2C9 Observations",)
    fovplot.ax.legend(legend_objects, legend_labels,
                      bbox_to_anchor=(0.1, 1., 1., 0.), loc=3,
                      ncol=len(legend_objects), borderaxespad=0.,
                      handlelength=0.8, frameon=False,
                      numpoints=1, scatterpoints=1)

    if len(positions) > 0 and size is not None:
        fovplot.ax.set_xlim([max(ra) + size/2., min(ra) - size/2.])
        fovplot.ax.set_ylim([min(dec) - size/2., max(dec) + size/2.])

    img = BytesIO()
    fovplot.fig.savefig(img)
    img.seek(0)
    response = flask.send_file(img, mimetype="image/png")
    return response

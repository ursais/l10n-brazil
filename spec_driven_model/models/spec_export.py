# Copyright 2019 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import models, fields

try:
    from nfelib.v4_00 import leiauteNFe  # FIXME: Move me to my module!
except ImportError:
    pass

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

_logger = logging.getLogger(__name__)


class AbstractSpecMixin(models.AbstractModel):
    _inherit = 'spec.mixin'

    def _get_ds_class(self, class_obj):
        #  FIXME: leiauteNFe hardcoded
        return getattr(leiauteNFe, class_obj._generateds_type)

    def _export_field(self, xsd_fields, class_obj, export_dict):
        # FIXME: Remove all references of nfe, make it generic!
        ds_class = self._get_ds_class(class_obj)
        ds_class_sepc = {i.name: i for i in ds_class.member_data_items_}

        for xsd_field in xsd_fields:
            # TODO: Export number required fields with Zero.
            xsd_required = class_obj._fields[xsd_field]._attrs.get(
                'xsd_required')
            # FIXME: xsd_field.replace(class_obj._field_prefix, '')
            field_spec_name = xsd_field.replace('nfe40_', '')
            member_spec = ds_class_sepc[field_spec_name]

            if __debug__:
                _logger.info(
                    "Field: %s, xsd_required=%s, type(%s)/%s = %s",
                    xsd_field,
                    xsd_required,
                    self._fields[xsd_field].type,
                    member_spec.data_type[0],
                    self[xsd_field]
                )

            if xsd_field == 'nfe40_tpAmb':
                self.env.context = dict(self.env.context)
                self.env.context.update({'tpAmb': self[xsd_field]})

            if self._fields[xsd_field].type == 'many2one':
                if not self[xsd_field] and not xsd_required:
                    if class_obj._fields[xsd_field].comodel_name \
                            not in self._get_spec_classes():
                        continue
                    if not any(self[f] for f in self[xsd_field]._fields
                               if self._fields[f]._attrs.get('xsd')) and \
                            xsd_field not in ['nfe40_PIS', 'nfe40_COFINS']:
                        continue
                if xsd_field == 'nfe40_ISSQN' and \
                        self.product_id.type == 'consu':
                    continue
                if xsd_field == 'nfe40_ISSQNtot' and all(
                        t == 'consu' for t in
                        self.nfe40_det.mapped('product_id.type')
                ):
                    continue
                if xsd_field in ['nfe40_II', 'nfe40_PISST', 'nfe40_COFINSST']:
                    continue
                field_data = self._export_many2one(xsd_field, class_obj)
            elif self._fields[xsd_field].type == 'one2many':
                field_data = self._export_one2many(xsd_field, class_obj)
            elif self._fields[xsd_field].type == 'datetime' and \
                    self[xsd_field]:
                field_data = self._export_datetime(xsd_field)
            elif self._fields[xsd_field].type == 'date' and self[xsd_field]:
                field_data = self._export_date(xsd_field)
            elif self._fields[xsd_field].type in ('float', 'monetary') and \
                    self[xsd_field] is not False:
                if xsd_field == 'nfe40_vProd':
                    if class_obj._name == 'nfe.40.prod':
                        self[xsd_field] = self['nfe40_qCom'] * \
                                          self['nfe40_vUnCom']
                    elif class_obj._name == 'nfe.40.icmstot':
                        self[xsd_field] = sum(
                            self['nfe40_det'].mapped('nfe40_vProd'))
                if xsd_field == 'nfe40_pICMSInterPart':
                    self[xsd_field] = 100.0
                if not self[xsd_field] and not xsd_required:
                    if not (class_obj._name == 'nfe.40.imposto' and
                            xsd_field == 'nfe40_vTotTrib') and not \
                            (class_obj._name == 'nfe.40.fat'):
                        continue
                field_data = self._export_float_monetary(
                    xsd_field, member_spec)
            else:
                field_data = self[xsd_field]
                if xsd_field == 'nfe40_xNome' and \
                        class_obj._name == 'nfe.40.dest' and \
                        self.env.context.get('tpAmb') == '2':
                    field_data = 'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO' \
                                 ' - SEM VALOR FISCAL'
                if xsd_field == 'nfe40_modBC':
                    field_data = self['icms_base_type']
                if xsd_field in ['nfe40_cEAN', 'nfe40_cEANTrib'] and \
                        not field_data:
                    field_data = 'SEM GTIN'
                if xsd_field == 'nfe40_CST':
                    if class_obj._name.startswith('nfe.40.icms'):
                        field_data = self.icms_cst_id.code
                    elif class_obj._name.startswith('nfe.40.ipi'):
                        field_data = self.ipi_cst_id.code
                    elif class_obj._name.startswith('nfe.40.pis'):
                        field_data = self.pis_cst_id.code
                    elif class_obj._name.startswith('nfe.40.cofins'):
                        field_data = self.cofins_cst_id.code

            if not self[xsd_field] and not field_data:
                continue

            if __debug__:
                _logger.info("Export: %s", field_data)

            export_dict[field_spec_name] = field_data

    def _export_many2one(self, field_name, class_obj=None):
        if self._fields[field_name]._attrs.get('original_spec_model'):
            field_data = self[field_name]._build_generateds(
                class_name=self._fields[field_name]._attrs.get(
                    'original_spec_model')
            )
        else:
            # continue
            if self[field_name]:
                field_data = self[field_name]._build_generateds(
                    class_obj._fields[field_name].comodel_name)
            else:
                field_data = self._build_generateds(
                    class_obj._fields[field_name].comodel_name)
        return field_data

    def _export_one2many(self, field_name, class_obj=None):
        relational_data = []
        for relational_field in self[field_name]:
            relational_data.append(
                relational_field._build_generateds(
                    class_obj._fields[field_name].comodel_name
                )
            )
        return relational_data

    def _export_float_monetary(self, field_name, member_spec):
        if member_spec.data_type[0]:
            TDec = ''.join(filter(lambda x: x.isdigit(),
                                  member_spec.data_type[0]))[-2:]
            my_format = "%.{0}f".format(TDec)
            return str(my_format % self[field_name])
        else:
            raise NotImplementedError

    def _export_date(self, field_name):
        return str(self[field_name])

    def _export_datetime(self, field_name):
        return str(fields.Datetime.context_timestamp(
            self,
            fields.Datetime.from_string(self[field_name])
        ).isoformat('T'))

    def _get_model_classes(self):
        classes = [getattr(x, '_name', None) for x in type(self).mro()]
        return classes

    def _get_spec_classes(self, classes=False):
        if not classes:
            classes = self._get_model_classes()
        spec_classes = []
        for c in set(classes):
            if c is None:
                continue
            if 'nfe.' not in c:  # make generic brittle
                continue
            # the following filter to fields to show
            # when several XSD class are injected in the same object
            if self._context.get('spec_class') and c != self._context[
                    'spec_class']:
                continue
            spec_classes.append(c)
        return spec_classes

    def _build_generateds(self, class_name=False):
        if not class_name:
            if hasattr(self, '_stacked'):
                class_name = self._stacked
            else:
                class_name = self._name

        class_obj = self.env[class_name]
        if not class_obj._generateds_type:
            return

        xsd_fields = (
            i for i in self.env[class_name]._fields if
            self.env[class_name]._fields[i]._attrs.get('xsd')
        )

        kwargs = {}

        ds_class = self._get_ds_class(class_obj)
        self._export_field(xsd_fields, class_obj, export_dict=kwargs)

        if kwargs:
            ds_object = ds_class(**kwargs)
            return ds_object

    def _print_xml(self, ds_object):
        if not ds_object:
            return
        output = StringIO()
        ds_object.export(
            output,
            0,
            pretty_print=True,
        )
        contents = output.getvalue()
        output.close()
        _logger.info(contents)

    def export_xml(self, print_xml=True):
        result = []

        if hasattr(self, '_stacked'):
            ds_object = self._build_generateds()
            if print_xml:
                self._print_xml(ds_object)
            result.append(ds_object)

        else:
            spec_classes = self._get_spec_classes()
            for class_name in spec_classes:
                ds_object = self._build_generateds(class_name)
                if print:
                    self._print_xml(ds_object)
                result.append(ds_object)
        return result

    def export_ds(self):
        return self.export_xml(print_xml=False)

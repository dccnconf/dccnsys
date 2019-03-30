(function ($) {

  $.fn.reorder = function () {
    const $list = this.find('.dccn-reorder-list');
    const form = this.find('.dccn-reorder-form');
    const $input = this.find('.dccn-reorder-form-input');
    const prev = {value: undefined};

    $input.change(function () {
      form.submit();
    });

    const fillInput = () => {
      const $items = this.find('.dccn-reorder-list-item');
      const ids = $.map($items, item => { return $(item).attr('data-id'); });
      $input.val(String(ids));
      if (prev.value === undefined) {
        prev.value = $input.val();
      } else if (prev.value !== $input.val()) {
        $input.trigger('change');
      }
    };

    $list.sortable({
      revert: true,
      stop: fillInput,   /* update input only after dragging is over */
      create: fillInput  /* we guarantee that input is always filled */
    });
  };

  $('.dccn-reorder').reorder();
}(jQuery));

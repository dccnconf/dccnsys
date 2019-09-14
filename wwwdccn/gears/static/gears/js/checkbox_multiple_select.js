$(document).ready(function () {
  $('.clear-cb-btn').on('click', function () {
    const parent = $(this).parent().parent();
    parent.find('.form-check input').prop('checked', false);
  });

  $('.select-all-cb-btn').on('click', function () {
    const parent = $(this).parent().parent();
    parent.find('.form-check input').prop('checked', true);
  });

  const tail = $('.cb-options-tail');

  const getNumChecked = function (el) {
    return el.find('input[type="checkbox"][checked]').length;
  };

  const getNumItems = function (el) {
    return el.find('input[type="checkbox"]').length;
  };

  tail.on('show.bs.collapse', function () {
    const collapse = $(this).siblings('.cb-options-tail-collapse');
    const numItems = getNumItems($(this));
    collapse.html(`<i class="fas fa-minus"></i> Show ${numItems} less...`);
    console.log(getNumChecked(collapse.parent()));
  });

  tail.on('hide.bs.collapse', function () {
    const collapse = $(this).siblings('.cb-options-tail-collapse');
    const numItems = getNumItems($(this));
    collapse.html(`<i class="fas fa-plus"></i> Show ${numItems} more...`);
  });

  // Initially de-collapse all selects with checked options:
  const selects = $('.checkbox-multiple-select');
  selects.each(function (index, el) {
    el = $(el);

    // First, we update titles on collapse anchors to represent the number of items hidden:
    const collapse = el.find('.cb-options-tail-collapse');
    if (collapse.length > 0) {
      const collapsedDiv = collapse.siblings('.cb-options-tail');
      collapse.html(`<i class="fas fa-plus"></i> Show ${getNumItems(collapsedDiv)} more...`);
    }

    // Secondly, force un-collapse of any select where at least one item checked:
    if (getNumChecked(el) > 0) {
      el.find('.cb-options-tail').collapse('show');
    }
  });
});

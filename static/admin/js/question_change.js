jQuery(document).ready(function ($) {
    (function ($) {
        $(function () {
            
            $('.tox-tinymce').css('height', '200px');
            var answer_type = $('#id_answer_type'),
                options = $('#options-group'),
                range_options = $('#range_options-group'),
                combinations = $('#optioncombination_set-group'),
                bool_points = $('.field-bool_points'),
                max_points = $('.field-max_points');

            function toggleVerified(value) {
                console.log(value)
                if (value === 'BL') {
                    bool_points.show();
                    options.hide();
                    range_options.hide();
                    combinations.hide();
                    max_points.hide();
                } else if (value === 'LST') {
                    bool_points.hide();
                    options.show();
                    range_options.hide();
                    combinations.hide();
                    max_points.hide();
                } else if (value === 'PRC') {
                    bool_points.hide();
                    options.hide();
                    range_options.show();
                    combinations.hide();
                    max_points.hide();
                } else if (value === 'NMBR') {
                    bool_points.hide();
                    options.hide();
                    range_options.show();
                    combinations.hide();
                    max_points.hide();
                } else if (value === 'MULT') {
                    bool_points.hide();
                    options.show();
                    range_options.hide();
                    combinations.show();
                    max_points.show();
                } else {
                    bool_points.hide();
                    options.hide();
                    range_options.hide();
                    combinations.hide();
                    max_points.hide();
                }
            }

            // show/hide on load based on pervious value of selectField
            
            toggleVerified(answer_type.val());

            // show/hide on change
            answer_type.change(function () {
                console.log($(this))
                toggleVerified($(this).val());
            });
        });
    })(django.jQuery);
});
$(document).ready(function () {
    $('#collegeSearchBar').on('click', function () {
        $('#collegeSearchCardModal').show();
    });

    $('#closeSearchModalButton').on('click', function () {
        $('#collegeSearchCardModal').hide();
        $('.searchCardBody').empty();
        $('#collegeSearchContentBar').val('');
    });

    $(document).keydown(function (event) {
        if (event.key == 'Escape') {
            $('#collegeSearchCardModal').hide();
            $('.searchCardBody').empty();
            $('#collegeSearchContentBar').val('');
        }
    });


    $(document).click(function (event) {
        if (!$(event.target).closest('#find-colleges').length && !$(event.target).closest('.searchCard').length) {
            $('#collegeSearchCardModal').hide();
            $('.searchCardBody').empty();
            $('#collegeSearchContentBar').val('');
        }
    });


    $('#collegeSearchContentBar').on('input', function () {
        var query = $(this).val();

        if (query.trim() === '') {
            // If the search bar is empty, clear the results
            $('.searchCardBody').empty();
        } else {
            // If the search bar has input, perform the search
            $.ajax({
                url: '/colleges/find/',
                data: {
                    'query': query
                },
                dataType: 'json',
                success: function (data) {
                    $('.searchCardBody').empty();  // Clear previous results

                    // Append each result to the search card body
                    if (data.no_results) {
                        $('.searchCardBody').html(data.no_results_html);
                    } else {
                        // Append each result to the search card body
                        $.each(data.results_html, function (index, resultHtml) {
                            $('.searchCardBody').append(resultHtml);
                        });
                    }

                    $('#collegeSearchCardModal').show();  // Show modal with results
                }
            });
        }
    });
});
define([
    'jquery',
    'knockout',
], function ($, ko) {
    // Apply aria attributes to the element when an observable changes between true and false
    // e.g. <div data-bind="onReportSectionToggleAria: visible.names, sectionName: '{% trans "Section Name" %}'"></div>
    ko.bindingHandlers.onReportSectionToggleAria = {
        update: function (element, valueAccessor, allBindings) {
            const value = ko.utils.unwrapObservable(valueAccessor());
            const sectionName = allBindings.get('sectionName') || '';

            function setAriaAttributes(isExpanded) {
                const ariaExpanded = isExpanded ? 'true' : 'false';
                const ariaLabel = `Section ${sectionName} ${isExpanded ? 'expanded' : 'collapsed'}`;
                const addClass = isExpanded ? 'fa-angle-double-right' : 'fa-angle-double-up';
                const removeClass = isExpanded ? 'fa-angle-double-up' : 'fa-angle-double-right';

                $(element).attr('aria-expanded', ariaExpanded);
                $(element).attr('aria-label', ariaLabel);
                $(element).addClass(addClass);
                $(element).removeClass(removeClass);
            }

            setAriaAttributes(value);
        }
    };

    return;
});
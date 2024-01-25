// For all the select using autocomplete light, add a listener to the open event
// and change the placeholder of the search input.
// There is no built-in way to do this, hence the hack.
// See https://forums.select2.org/t/additional-placeholder-in-search-input/325
$("select[data-autocomplete-light-url]").map((idx, el) =>
  $(el).one("select2:open", (e) => {
    $("input.select2-search__field").prop(
      "placeholder",
      "Entrez une valeur ici pour rechercher dans la liste"
    );
  })
);

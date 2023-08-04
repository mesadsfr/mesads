import Alpine from "alpinejs";
import SetupFormsetFiles from "../formset_files";

SetupFormsetFiles();

// array.findLastIndex is only available for firefox>104
function findLastIndex(arr: any[], func: (e: any) => boolean) {
  for (let i = arr.length; i > 0; --i) {
    if (func(arr[i - 1])) {
      return i - 1;
    }
  }
  return -1;
}

type DataType = {
  ads_creation_date: string;
  used_by_owner: string;
  attribution_type: string;
};

const data = JSON.parse(
  (document.getElementById("data") as HTMLScriptElement).text
) as DataType;

Alpine.data("get_x_data", () => ({
  ads_creation_date: data.ads_creation_date,

  get ads_before_2014() {
    const creation_date = new Date(this.ads_creation_date);
    if (creation_date < new Date("2014-10-01")) {
      return true;
    }
    return false;
  },

  // The field "attribution_date" should only be displayed for old ADS, or if the creation date is not set
  get should_display_attribution_date() {
    return !this.ads_creation_date || this.ads_before_2014;
  },

  used_by_owner: data.used_by_owner,

  // The field "owner_license_number" should always be displayed for new ADS.
  // For old ADS, it should only be displayed if the field "used_by_owner" is
  // set to "true"
  get should_display_owner_license_number() {
    return (
      !this.ads_before_2014 ||
      this.used_by_owner === "true" ||
      this.used_by_owner === "unknown"
    );
  },

  attribution_type: data.attribution_type,

  extraADSUserForms: 0,
}));

Alpine.directive("add-ads-user-button", (el, { expression }, { evaluate }) => {
  el.addEventListener("click", () => {
    const form = document.getElementById("ads-users");
    if (!form) {
      throw new Error("ads-users div not found");
    }

    // Retrieve the value of the "extraADSUserForms" x-data attribute
    const extra = evaluate("extraADSUserForms") as number;

    // For each entry, replace the string __prefix__ present in the id and name by the form index.
    el.parentElement
      ?.querySelectorAll(".fr-form-group")
      .forEach((value, index) => {
        const div = value as HTMLDivElement;

        div.querySelectorAll("input").forEach((input) => {
          input.id = input.id.replace(/__prefix__/g, index.toString());
          input.name = input.name.replace(/__prefix__/, index.toString());
        });
      });

    // Update the hidden field TOTAL_FORMS to let Django know how many forms to process
    const totalInput = Array.from(
      form.querySelectorAll("input[type=hidden]")
    ).find((form) => form.id.match(/TOTAL_FORMS/)) as HTMLInputElement;
    totalInput.value = (parseInt(totalInput.value, 10) + 1).toString();
  });
});

Alpine.start();

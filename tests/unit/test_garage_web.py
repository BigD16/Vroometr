from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
_GARAGE_PAGE = (_WEB / "app" / "(shell)" / "garage" / "page.tsx").read_text()
_NEW_PAGE = (_WEB / "app" / "(shell)" / "garage" / "new" / "page.tsx").read_text()
_DETAIL_PAGE = (
    _WEB / "app" / "(shell)" / "garage" / "[bikeId]" / "page.tsx"
).read_text()
_EDIT_PAGE = (
    _WEB / "app" / "(shell)" / "garage" / "[bikeId]" / "edit" / "page.tsx"
).read_text()
_BIKE_FORM = (_WEB / "components" / "BikeForm.tsx").read_text()
_BIKE_DETAILS = (_WEB / "components" / "BikeDetails.tsx").read_text()
_GARAGE_LIST = (_WEB / "components" / "GarageList.tsx").read_text()
_ACTIVE_SELECTOR = (_WEB / "components" / "ActiveBikeSelector.tsx").read_text()
_BIKES_ROUTE = (_WEB / "app" / "api" / "bikes" / "route.ts").read_text()
_BIKE_ROUTE = (
    _WEB / "app" / "api" / "bikes" / "[bikeId]" / "route.ts"
).read_text()


def test_garage_has_list_create_detail_and_edit_routes() -> None:
    assert "<GarageList />" in _GARAGE_PAGE
    assert "<BikeForm />" in _NEW_PAGE
    assert "loadBike(bikeId)" in _DETAIL_PAGE
    assert "<BikeDetails bike={bike} />" in _DETAIL_PAGE
    assert "loadBike(bikeId)" in _EDIT_PAGE
    assert "<BikeForm bike={bike} />" in _EDIT_PAGE


def test_garage_mutations_use_authenticated_next_routes() -> None:
    assert "export async function POST" in _BIKES_ROUTE
    assert 'proxyFastApi("/v1/bikes"' in _BIKES_ROUTE
    assert "export async function GET" in _BIKE_ROUTE
    assert "export async function PATCH" in _BIKE_ROUTE
    assert "proxyFastApi(bikePath(bikeId)" in _BIKE_ROUTE
    assert "export async function DELETE" not in _BIKE_ROUTE


def test_create_selects_new_bike_and_archive_is_reversible() -> None:
    assert 'editing ? "PATCH" : "POST"' in _BIKE_FORM
    assert "await reload();" in _BIKE_FORM
    assert "await selectBike(savedBike.id);" in _BIKE_FORM
    assert 'body: JSON.stringify({ status: "active" })' in _GARAGE_LIST
    assert "Archived" in _GARAGE_LIST
    assert "Restore" in _GARAGE_LIST


def test_garage_supports_electric_bikes_and_defaults_to_metric() -> None:
    assert 'name="powertrain_type"' in _BIKE_FORM
    assert 'powertrainType === "combustion"' in _BIKE_FORM
    assert 'powertrainType === "combustion" ? nullableNumber' in _BIKE_FORM
    assert 'bike?.unit_preference ?? "metric"' in _BIKE_FORM
    assert 'bike.powertrain_type === "electric"' in _GARAGE_LIST
    assert 'bike.powertrain_type === "electric"' in _BIKE_DETAILS
    assert 'bike.powertrain_type === "electric"' in _ACTIVE_SELECTOR

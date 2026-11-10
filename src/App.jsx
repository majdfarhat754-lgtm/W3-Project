import { useEffect, useState } from "react";

const formatPrice = (price) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: import.meta.env.VITE_CURRENCY || "USD",
    maximumFractionDigits: 2,
  }).format(price);

function App() {
  const [cars, setCars] = useState([]);
  const [search, setSearch] = useState("");
  const [activeMake, setActiveMake] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedCar, setSelectedCar] = useState(null);
  const [dealType, setDealType] = useState("purchase");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [requestResult, setRequestResult] = useState(null);
  const [pickupDate, setPickupDate] = useState("");
  const checkoutResult = new URLSearchParams(window.location.search).get("checkout");
  const checkoutKind = new URLSearchParams(window.location.search).get("kind");
  const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 10);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams();
    if (search.trim()) params.set("q", search.trim());
    if (activeMake) params.set("make", activeMake);

    setLoading(true);
    setError("");

    fetch(`/api/cars/?${params}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Inventory could not be loaded.");
        return response.json();
      })
      .then((data) => setCars(data.results ?? data))
      .catch((fetchError) => {
        if (fetchError.name !== "AbortError") {
          setError("We couldn't connect to the inventory. Please try again shortly.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [search, activeMake]);

  useEffect(() => {
    if (!selectedCar) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === "Escape" && !submitting) setSelectedCar(null);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [selectedCar, submitting]);

  const openRequest = (car, type) => {
    setSelectedCar(car);
    setDealType(type);
    setFormError("");
    setRequestResult(null);
    setPickupDate("");
  };

  const nextDate = (value) => {
    const date = new Date(`${value}T00:00:00`);
    date.setDate(date.getDate() + 1);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  };

  const handleDealSubmit = async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const checkout = event.nativeEvent.submitter?.value === "checkout";
    const payload = {
      car_id: selectedCar.id,
      customer_name: formData.get("customer_name"),
      email: formData.get("email"),
      phone: formData.get("phone"),
      checkout,
    };
    const endpoint = dealType === "purchase" ? "/api/purchase-requests/" : "/api/rental-bookings/";

    if (dealType === "purchase") {
      payload.notes = formData.get("notes");
    } else {
      payload.pickup_date = formData.get("pickup_date");
      payload.return_date = formData.get("return_date");
    }

    setSubmitting(true);
    setFormError("");
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "We couldn't submit your request.");
      if (data.checkout_url) {
        window.location.assign(data.checkout_url);
        return;
      }
      setRequestResult(data);
    } catch (submitError) {
      setFormError(submitError.message || "We couldn't submit your request. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <header className="site-header">
        <a className="brand" href="#" aria-label="Northline Motors home">
          <span className="brand-mark">N</span>
          <span>NORTHLINE<span className="brand-light"> MOTORS</span></span>
        </a>
        <nav className="main-nav" aria-label="Main navigation">
          <a className="nav-active" href="#inventory">Inventory</a>
          <a href="#about">Our story</a>
          <a href="#contact">Contact</a>
        </nav>
        <a className="header-phone" href="tel:+15550142000">
          <span className="phone-icon" aria-hidden="true">↗</span>
          (555) 014-2000
        </a>
      </header>

      {checkoutResult && (
        <div className={`checkout-banner ${checkoutResult === "success" ? "checkout-success" : ""}`} role="status">
          {checkoutResult === "success"
            ? `Your ${checkoutKind === "rental" ? "rental payment" : "purchase payment"} was submitted. The dealership will confirm the ${checkoutKind === "rental" ? "booking" : "vehicle purchase"} after payment verification.`
            : "Checkout was cancelled. No payment was completed."}
        </div>
      )}

      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow"><span /> THE ROAD IS YOURS</p>
            <h1>Find your<br />next <em>drive.</em></h1>
            <p className="hero-description">
              Good cars. Good people. No guesswork.<br />
              Your next chapter starts right here.
            </p>
            <a className="button button-dark" href="#inventory">
              Explore our inventory <span aria-hidden="true">↘</span>
            </a>
            <div className="hero-note">
              <span className="note-line" />
              <span>QUALITY CARS, WITHOUT THE RUNAROUND.</span>
            </div>
          </div>
          <div className="hero-image" role="img" aria-label="A classic car on an open road">
            <div className="image-caption">
              <span>01 / MADE FOR THE LONG WAY</span>
              <span className="caption-arrow">↗</span>
            </div>
          </div>
          <div className="hero-index">EST. 2012 &nbsp;·&nbsp; INDEPENDENT BY NATURE</div>
        </section>

        <section className="inventory-section" id="inventory">
          <div className="section-heading">
            <div>
              <p className="eyebrow">THE GOOD STUFF</p>
              <h2>Find your kind of <em>car.</em></h2>
            </div>
            <p className="inventory-intro">
              Every car has a story. Let’s find the one<br className="desktop-break" /> that fits yours.
            </p>
          </div>

          <div className="inventory-toolbar">
            <div className="filter-list" aria-label="Filter by make">
              {["All cars", "Audi", "BMW", "Mercedes-Benz", "Porsche"].map((make) => {
                const value = make === "All cars" ? "" : make;
                return (
                  <button
                    className={`filter-button ${activeMake === value ? "selected" : ""}`}
                    key={make}
                    onClick={() => setActiveMake(value)}
                    type="button"
                  >
                    {make}
                  </button>
                );
              })}
            </div>
            <label className="search-box">
              <span aria-hidden="true">⌕</span>
              <input
                aria-label="Search inventory"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search inventory"
                type="search"
                value={search}
              />
              <kbd>/</kbd>
            </label>
          </div>

          {error ? (
            <div className="inventory-message" role="alert">{error}</div>
          ) : loading ? (
            <div className="inventory-message" role="status">Finding the right cars for you…</div>
          ) : cars.length === 0 ? (
            <div className="inventory-message">
              No cars found. Try a different search or check back soon.
            </div>
          ) : (
            <div className="car-grid">
              {cars.map((car) => (
                <article className="car-card" key={car.id}>
                  <div className="car-image-wrap">
                    <img alt={`${car.year} ${car.make} ${car.model}`} loading="lazy" src={car.image_url} />
                    {car.featured && <span className="car-badge">NORTHLINE PICK</span>}
                    <span className="car-year">{car.year}</span>
                  </div>
                  <div className="car-details">
                    <div className="car-name-row">
                      <div>
                        <p className="car-make">{car.make}</p>
                        <h3>{car.model}</h3>
                      </div>
                      <span className="car-price">{formatPrice(car.price)}</span>
                    </div>
                    <div className="car-specs">
                      <span>{Number(car.mileage).toLocaleString()} mi</span>
                      <span>{car.transmission}</span>
                      <span>{car.fuel_type}</span>
                    </div>
                    <div className="car-actions">
                      <button
                        className="car-action car-action-primary"
                        onClick={() => openRequest(car, "purchase")}
                        type="button"
                      >
                        Buy or ask
                      </button>
                      <button
                        className="car-action"
                        onClick={() => openRequest(car, "rental")}
                        type="button"
                      >
                        Rent{Number(car.rental_daily_rate) > 0
                          ? ` · ${formatPrice(car.rental_daily_rate)}/day`
                          : ""}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
          {!loading && !error && cars.length > 0 && (
            <p className="results-count">SHOWING {cars.length} VEHICLE{cars.length === 1 ? "" : "S"}</p>
          )}
        </section>

        <section className="about-section" id="about">
          <p className="eyebrow">A BETTER WAY TO BUY</p>
          <div className="about-content">
            <h2>People first.<br /><em>Always.</em></h2>
            <div>
              <p>
                Buying a car should feel exciting, not exhausting. We’re a small,
                independent team that believes in straight answers, carefully
                chosen cars, and treating people like people.
              </p>
              <a className="text-link" href="#contact">Come say hello <span aria-hidden="true">↗</span></a>
            </div>
          </div>
        </section>

        <section className="contact-strip" id="contact">
          <div>
            <p className="eyebrow">YOUR NEXT DRIVE IS CLOSER THAN YOU THINK</p>
            <h2>Let’s get you <em>moving.</em></h2>
          </div>
          <a className="button button-light" href="mailto:hello@northlinemotors.example">
            Talk to our team <span aria-hidden="true">↗</span>
          </a>
        </section>
      </main>

      {selectedCar && (
        <div
          className="dialog-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !submitting) setSelectedCar(null);
          }}
        >
          <section aria-labelledby="deal-dialog-title" aria-modal="true" className="deal-dialog" role="dialog">
            <button
              aria-label="Close dialog"
              className="dialog-close"
              disabled={submitting}
              onClick={() => setSelectedCar(null)}
              type="button"
            >
              ×
            </button>
            {requestResult ? (
              <div className="request-complete">
                <p className="eyebrow">REQUEST RECEIVED</p>
                <h2 id="deal-dialog-title">You’re one step <em>closer.</em></h2>
                <p>
                  We’ve received your {dealType === "purchase" ? "purchase" : "rental"} request
                  for the {selectedCar.year} {selectedCar.make} {selectedCar.model}.
                  Our team will follow up using the contact details you provided.
                </p>
                {dealType === "rental" && Number(requestResult.total_amount) > 0 && (
                  <p className="request-total">
                    Estimated rental total: {formatPrice(requestResult.total_amount)}
                    {" "}for {requestResult.days} day{requestResult.days === 1 ? "" : "s"}.
                    Final availability and terms are confirmed by the dealership.
                  </p>
                )}
                <div className="paperwork-checklist">
                  <h3>Paperwork checklist</h3>
                  <ul>
                    {(dealType === "purchase"
                      ? ["Government-issued photo ID", "Proof of insurance", "Payment or financing details"]
                      : ["Valid driver's license", "Proof of insurance or coverage selection", "Payment card and rental agreement"]
                    ).map((item) => <li key={item}>{item}</li>)}
                  </ul>
                  <p>
                    General checklist only. Local requirements vary; the dealership will
                    confirm the documents needed. Agreements are completed with the dealer.
                  </p>
                </div>
                <button className="button button-dark dialog-done" onClick={() => setSelectedCar(null)} type="button">
                  Done <span aria-hidden="true">↗</span>
                </button>
              </div>
            ) : (
              <>
                <p className="eyebrow">{dealType === "purchase" ? "MAKE IT YOURS" : "PLAN YOUR DRIVE"}</p>
                <h2 id="deal-dialog-title">
                  {dealType === "purchase" ? "Purchase this car." : "Request a rental."}
                </h2>
                <p className="dialog-car">
                  {selectedCar.year} {selectedCar.make} {selectedCar.model}
                  {dealType === "purchase"
                    ? ` · ${formatPrice(selectedCar.price)}`
                    : ` · ${Number(selectedCar.rental_daily_rate) > 0
                      ? `${formatPrice(selectedCar.rental_daily_rate)} per day`
                      : "Ask us for a rental rate"}`}
                </p>
                <form className="deal-form" onSubmit={handleDealSubmit}>
                  {dealType === "rental" && (
                    <div className="date-fields">
                      <label>
                        Pickup date
                        <input
                          min={today}
                          name="pickup_date"
                          onChange={(event) => setPickupDate(event.target.value)}
                          required
                          type="date"
                        />
                      </label>
                      <label>
                        Return date
                        <input min={pickupDate ? nextDate(pickupDate) : today} name="return_date" required type="date" />
                      </label>
                    </div>
                  )}
                  <label>
                    Full name
                    <input autoComplete="name" maxLength="120" name="customer_name" required />
                  </label>
                  <label>
                    Email
                    <input autoComplete="email" name="email" required type="email" />
                  </label>
                  <label>
                    Phone
                    <input autoComplete="tel" maxLength="30" name="phone" required type="tel" />
                  </label>
                  {dealType === "purchase" && (
                    <label>
                      Questions or notes <span className="optional-label">(optional)</span>
                      <textarea maxLength="1000" name="notes" rows="2" />
                    </label>
                  )}
                  {dealType === "purchase" && (
                    <p className="checkout-disclaimer">
                      Online checkout charges the advertised vehicle price only.
                      Taxes, title, registration, and other fees are not included.
                      This payment is not a signed purchase contract.
                    </p>
                  )}
                  {dealType === "rental" && (
                    <p className="checkout-disclaimer">
                      Rental dates are requests until availability and terms are confirmed.
                      The listed estimate excludes any taxes, deposits, or additional fees.
                    </p>
                  )}
                  {formError && <p className="form-error" role="alert">{formError}</p>}
                  <div className="form-actions">
                    <button className="button button-outline" disabled={submitting} name="action" type="submit" value="request">
                      {submitting ? "Sending…" : "Send a request"}
                    </button>
                    <button
                      className="button button-dark"
                      disabled={submitting || (dealType === "rental" && Number(selectedCar.rental_daily_rate) <= 0)}
                      name="action"
                      type="submit"
                      value="checkout"
                    >
                      {submitting ? "Please wait…" : "Continue to secure checkout"}
                      <span aria-hidden="true">↗</span>
                    </button>
                  </div>
                  <p className="privacy-note">
                    We use your details to respond to this request. Don’t include payment card
                    or driver’s license numbers in the message.
                  </p>
                </form>
              </>
            )}
          </section>
        </div>
      )}

      <footer className="site-footer">
        <a className="brand footer-brand" href="#">
          <span className="brand-mark">N</span>
          <span>NORTHLINE<span className="brand-light"> MOTORS</span></span>
        </a>
        <span>GOOD CARS. GOOD PEOPLE. &copy; {new Date().getFullYear()} NORTHLINE MOTORS.</span>
        <a href="tel:+15550142000">(555) 014-2000</a>
      </footer>
    </>
  );
}

export default App;

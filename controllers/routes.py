from flask import Blueprint, abort, jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_user, current_user, login_required, logout_user
from models.models import User, Lots, Spots, db, Bookings
from datetime import datetime

bp = Blueprint("main", __name__)


#------ADMIN---
@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        uname = request.form["uname"]
        upass = request.form["upass"]
        admin = User.query.filter_by(username=uname, password=upass, role="admin").first()
        if admin:
            login_user(admin)
            return redirect(url_for("main.admin_home"))
        else:
            flash("No match found. Try again.")
    return render_template("admin_login.html")


@bp.route("/admin/dashboard")
@login_required
def admin_home():
    if current_user.role != "admin":
        abort(403)
    all_lots = Lots.query.all()
    all_spots = {lot.id: Spots.query.filter_by(lot_id=lot.id).all() for lot in all_lots}
    return render_template("admin_home.html", lots=all_lots, spots_map=all_spots)

@bp.route("/admin/add_lot", methods=["GET", "POST"])
@login_required
def add_lot():
    if current_user.role != "admin":
        return redirect(url_for("main.user_dashboard")) 

    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        pincode = request.form["pincode"]
        price = float(request.form["price"])
        max_spots = int(request.form["max_spots"])

        new_lot = Lots(name=name, address=address, pincode=pincode, price=price, max_spots=max_spots)
        db.session.add(new_lot)
        db.session.commit()

        for _ in range(max_spots):
            spot = Spots(lot_id=new_lot.id, status="E")
            db.session.add(spot)
        db.session.commit()

        flash("Lot added successfully.")
        return redirect(url_for("main.admin_home"))

    return render_template("add_lot.html")



@bp.route("/admin/delete-lot/<int:lot_id>", methods=["POST"])
def delete_lot(lot_id):
    lot = Lots.query.get_or_404(lot_id)
    occupied = Spots.query.filter_by(lot_id=lot.id, status="O").first()


    if occupied:
        flash("Cannot delete. Some spots are still occupied.")
    else:
        Spots.query.filter_by(lot_id=lot.id).delete()
        db.session.delete(lot)
        db.session.commit()
        flash("Lot deleted.")
        
    return redirect(url_for("main.admin_home"))

@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.pincode = request.form.get('pincode')
        current_user.address = request.form.get('address')
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('main.user_dashboard'))

    return render_template('edit_page.html', user=current_user)


#---------USER---
@bp.route("/user/login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        uname = request.form["uname"]
        upass = request.form["upass"]
        user = User.query.filter_by(username=uname, password=upass, role="user").first()
        if user:
            login_user(user)
            return redirect(url_for("main.user_dashboard"))
        else:
            flash("Invalid credentials")
    return render_template("main.html")

@bp.route("/user/dashboard")
@login_required
def user_dashboard():
    search_location = request.args.get("location", "").strip()
    searched = bool(search_location)

    if searched:
        lots = Lots.query.filter(Lots.address.ilike(f"%{search_location}%")).all()
    else:
        lots = Lots.query.all()

    for lot in lots:
        lot.spots = Spots.query.filter_by(lot_id=lot.id).all()

    total_bookings = Spots.query.filter_by(user_id=current_user.id).count()

    lot_data = [
        {"id": lot.id, "name": lot.name, "location": lot.address}
        for lot in lots
    ]

    return render_template("user_dashboard.html",
                           lots=lots,
                           total_bookings=total_bookings,
                           lot_data=lot_data,
                           searched=searched,
                           search_location=search_location)



@bp.route("/user/park/<int:lot_id>", methods=["POST"])
@login_required
def park_in(lot_id):
    spot = Spots.query.filter_by(lot_id=lot_id, status="E").first()
    if spot:
        spot.status = "O"
        spot.user_id = current_user.id
        spot.in_time = datetime.now()
        spot.vehicle_no = request.form["vehicle_no"]
        db.session.commit()
        flash(f"Spot {spot.id} allocated.")
    else:
        flash("No available spots.")
    return redirect(url_for("main.user_dashboard"))



    
@bp.route("/user/release", methods=["POST"])
@login_required
def release_spot():
    spot_id = request.form.get("spot_id")
    spot = Spots.query.get_or_404(spot_id)

    if spot.user_id == current_user.id and spot.status == "O":
        spot.status = "E"
        spot.out_time = datetime.now()

        duration = (spot.out_time - spot.in_time).total_seconds() / 3600 
        lot = Lots.query.get(spot.lot_id)
        cost = round(duration * lot.price, 2)

        vehicle_no = spot.vehicle_no
        db.session.commit()

        return render_template("release_summary.html", spot=spot, vehicle_no=vehicle_no,
                               duration=duration, cost=cost, lot=lot)
    else:
        flash("Invalid release attempt.")
        return redirect(url_for("main.user_dashboard"))
    

@bp.route("/api/spot/<int:spot_id>")
@login_required
def get_spot_details(spot_id):
    spot = Spots.query.get_or_404(spot_id)
    if spot.user_id != current_user.id or spot.status != "O":
        return jsonify({"error": "Unauthorized"}), 403

    out_time = datetime.now()
    duration = (out_time - spot.in_time).total_seconds() / 3600 

    lot = Lots.query.get(spot.lot_id)
    total_cost = round(duration * lot.price, 2)

    return jsonify({
        "spot_id": spot.id,
        "vehicle_no": spot.vehicle_no,
        "in_time": spot.in_time.strftime("%Y-%m-%d %H:%M:%S"),
        "out_time": out_time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_cost": total_cost
    })




@bp.route("/user/signup", methods=["GET", "POST"])
def user_signup():
    if request.method == "POST":
        uname = request.form["uname"]
        upass = request.form["upass"]
        full_name = request.form["full_name"]
        pincode = request.form["pincode"]
        address = request.form["address"]

        if User.query.filter_by(username=uname).first():
            flash("Username already exists.")
        else:
            new_user = User(
                username=uname,
                password=upass,
                full_name=full_name,
                pincode=pincode,
                address=address,
                role="user"
            )
            db.session.add(new_user)
            db.session.commit()
            flash("User registered successfully. Please log in.")
            return redirect(url_for("main.combined_login"))

    return render_template("user_signup.html")




@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.combined_login"))



@bp.route("/login", methods=["GET", "POST"])
def combined_login():
    if request.method == "POST":
        role = request.form["role"]
        uname = request.form["uname"]
        upass = request.form["upass"]

        user = User.query.filter_by(username=uname, password=upass, role=role).first()
        if user:
            login_user(user)
            if role == "admin":
                return redirect(url_for("main.admin_home"))
            else:
                return redirect(url_for("main.user_dashboard"))
        else:
            flash("Invalid credentials")
            return redirect(url_for("main.combined_login"))

    return render_template("main.html")




#-----------Summary
@bp.route("/user/summary")
@login_required
def user_summary():
    spots = Spots.query.filter_by(user_id=current_user.id).filter(Spots.out_time.isnot(None)).all()

    total_bookings = len(spots)
    total_hours = 0.0
    total_cost = 0.0
    labels = []
    data = []
    colors = []

    import random

    for spot in spots:
        lot = Lots.query.get(spot.lot_id)
        if not spot.in_time or not spot.out_time or not lot or lot.price is None:
            continue

        duration = (spot.out_time - spot.in_time).total_seconds() / 3600
        duration = float(duration) if duration else 0.0
        price = float(lot.price)

        cost = duration * price

        total_hours += duration
        total_cost += cost
        labels.append(f"Spot {spot.id}")
        data.append(float(f"{duration:.2f}"))

        r, g, b = random.randint(150, 255), random.randint(100, 255), random.randint(100, 255)
        colors.append(f"rgba({r},{g},{b},0.9)")

    total_hours_str = f"{total_hours:.2f}"
    total_cost_str = f"{total_cost:.2f}"

    return render_template("user_summary.html",
                           total_bookings=total_bookings,
                           total_hours=total_hours_str,
                           total_cost=total_cost_str,
                           labels=labels,
                           data=data,
                           colors=colors)


@bp.route("/admin/search-users")
@login_required
def search_users():
    if current_user.role != "admin":
        abort(403)
    query = request.args.get("q", "")
    users = User.query.filter(User.role == "user", User.username.ilike(f"%{query}%")).all()
    return render_template("admin_users.html", users=users, query=query)


@bp.route('/edit_lot', methods=['POST'])
def edit_lot():
    lot_id = request.form['lot_id']
    new_max_spots = int(request.form['max_spots'])

    lot = Lots.query.get(lot_id)
    if not lot:
        flash("Lot not found.")
        return redirect(url_for('main.admin_home'))

    current_count = Spots.query.filter_by(lot_id=lot.id).count()
    lot.max_spots = new_max_spots

    if new_max_spots > current_count:
        for _ in range(new_max_spots - current_count):
            db.session.add(Spots(lot_id=lot.id, status='E'))
    elif new_max_spots < current_count:
        occupied_spots = Spots.query.filter_by(lot_id=lot.id, status='O').count()
        removable_count = current_count - new_max_spots
        empty_spots = Spots.query.filter_by(lot_id=lot.id, status='E').limit(removable_count).all()

        if len(empty_spots) < removable_count:
            flash("Cannot reduce spots — some are occupied.")
            return redirect(url_for('main.admin_home'))

        for spot in empty_spots:
            db.session.delete(spot)

    db.session.commit()
    flash("Lot updated successfully!")
    return redirect(url_for('main.admin_home'))



@bp.route('/admin/search', methods=['GET'])
@login_required
def admin_search():
    query = request.args.get('query', '')

    users = User.query
    lots = Lots.query

    if query:
        users = users.filter(
            (User.username.ilike(f"%{query}%")) |
            (User.address.ilike(f"%{query}%")) |
            (User.pincode.ilike(f"%{query}%"))
        )
        lots = lots.filter(
            (Lots.address.ilike(f"%{query}%")) |
            (Lots.pincode.ilike(f"%{query}%")) |
            (Lots.name.ilike(f"%{query}%")) |
            (Lots.id.like(f"%{query}%"))
        )

    users = users.all()
    lots = lots.all()
    spots_map = {lot.id: Spots.query.filter_by(lot_id=lot.id).all() for lot in lots}
    return render_template("admin_search.html", users=users, lots=lots, spots_map=spots_map)


@bp.route('/admin/users')
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@bp.route("/admin/summary")
@login_required
def admin_summary():
    if current_user.role != "admin":
        return redirect(url_for("main.login"))

    lots = Lots.query.all()

    spot_data = []
    revenue_data = []

    for lot in lots:
        free_spots = sum(1 for spot in lot.spot_list if spot.status == "E")
        occupied_spots = sum(1 for spot in lot.spot_list if spot.status == "O")

        bookings = Bookings.query.join(Spots).filter(Spots.lot_id == lot.id).all()
        revenue = sum(booking.cost or 0 for booking in bookings)

        spot_data.append({
            "name": lot.name,
            "free": free_spots,
            "occupied": occupied_spots
        })

        revenue_data.append({
            "name": lot.name,
            "revenue": revenue
        })

    return render_template("admin_summary.html",
                           spot_data=spot_data,
                           revenue_data=revenue_data)



@bp.route("/admin/edit", methods=["GET", "POST"])
@login_required
def admin_edit():
    if current_user.role != "admin":
        abort(403)

    if request.method == "POST":
        current_user.full_name = request.form.get("full_name")
        current_user.pincode = request.form.get("pincode")
        current_user.address = request.form.get("address")
        db.session.commit()
        flash("Profile updated successfully!")
        return redirect(url_for("main.admin_home"))

    return render_template("admin_edit.html")

from common import bot, logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, RegexHandler
from .model import Category, Item, Order, OrderItem, Restaurant
import time, telegram, math

RESTAURANT_PER_PAGE = 4
CATEGORIES_PER_PAGE = 4
ITEMS_PER_PAGE = 5


def navigation_buttons(prefix, current_page, last_page):
    next_page = current_page+1 if current_page+1 <= last_page else last_page
    previous_page = current_page-1 if current_page-1 >= 1 else 1
    
    buttons = []
    if previous_page != 1 :
        buttons.append(InlineKeyboardButton("<<", callback_data="{prefix}_{page}".format(prefix=prefix, page=1)))
    if current_page != 1:
        buttons.append(InlineKeyboardButton("<", callback_data="{prefix}_{page}".format(prefix=prefix, page=str(previous_page))))
    if current_page != last_page:
        buttons.append(InlineKeyboardButton(">", callback_data="{prefix}_{page}".format(prefix=prefix, page=str(next_page))))
    if next_page != last_page:
        buttons.append(InlineKeyboardButton(">>", callback_data="{prefix}_{page}".format(prefix=prefix, page=str(last_page))))

    return buttons


def category(bot, update):
    category_id = int(update.callback_query.data.split("_")[1]) if update.callback_query else 1
    current_page = int(update.callback_query.data.split("_")[2]) if update.callback_query else 1

    category = Category.select().where(Category.id == category_id).get()
    all_items = Item.select().where(Item.category == category)
    total_pages = math.ceil(len(all_items)/ITEMS_PER_PAGE)

    if total_pages > 1:
        from_item = (current_page*ITEMS_PER_PAGE) - ITEMS_PER_PAGE
        to_item = current_page*ITEMS_PER_PAGE
        
        text = "Category '{name}'\npage {current}/{total}\n-------------------\n".format(name=category.name, current=current_page, total=total_pages)
        for item in all_items[from_item:to_item]:
            text += "<b>{name}</b>  {price:.2f} €\n<i>{description}</i>\n/order_{item_id}\n\n".format(name=item.name, 
                price=item.price, description=item.description, item_id=item.id) 

        keyboard = [navigation_buttons("category_{}".format(category_id), current_page, total_pages)]
        keyboard.append([InlineKeyboardButton("Categories", callback_data="categories_1")])
        update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=telegram.ParseMode.HTML)
    else:
        text = "Category '{name}'\npage 1/1\n-------------------\n".format(name=category.name)
        for item in all_items:
            text += "<b>{name}</b>  {price:.2f} €\n<i>{description}</i>\n/order_{item_id}\n\n".format(name=item.name, 
                price=item.price, description=item.description, item_id=item.id) 

        keyboard = [[InlineKeyboardButton("Categories", callback_data="categories_1")]]
        update.callback_query.edit_message_text(text=text, parse_mode=telegram.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))  


def categories(bot, update):
    current_page = int(update.callback_query.data.split("_")[1]) if update.callback_query else 1

    restaurant_selected = Restaurant.select().where(Restaurant.selected == True).get()
    all_categories = Category.select().where(Category.restaurant == restaurant_selected)
    total_pages = math.ceil(len(all_categories)/CATEGORIES_PER_PAGE)
    
    if total_pages > 1:
        from_item = (current_page*CATEGORIES_PER_PAGE) - CATEGORIES_PER_PAGE
        to_item = current_page*CATEGORIES_PER_PAGE
        keyboard = []
        for c in all_categories[from_item:to_item]:
            keyboard.append(
                [InlineKeyboardButton(c.name, callback_data="category_{}_1".format(c.id))]
            )

        keyboard.append(navigation_buttons("categories", current_page, total_pages))
    else:
        keyboard = []
        for c in all_categories:
            keyboard.append(
                [InlineKeyboardButton(c.name, callback_data="category_{}_1".format(c.id))]
            )

    if update.callback_query:
        update.callback_query.edit_message_text(text="Seleziona una categoria:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text(text="Seleziona una categoria:", reply_markup=InlineKeyboardMarkup(keyboard))


def order(bot, update):
    item_id = int(update.message.text.replace('/order_', '').split('@')[0])
    try:
        item = Item.get(Item.id == item_id)
        username = update.message.from_user.first_name
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id
        order = Order.select().where((Order.user_id == user_id) & (Order.chat_id == chat_id))
        if not order.exists():
            order = Order.create(chat_id=chat_id, user_id=user_id, username=username)
            order.save()

        order_item = OrderItem.select().where((OrderItem.order == order) & (OrderItem.item == item))
        if not order_item.exists():
            OrderItem.insert(
                order=order,
                item=item,
                quantity=1
            ).execute()
            update.message.reply_text("Added {item_name} to order".format(item_name=item.name))
        else:
            OrderItem \
                .update({OrderItem.quantity: OrderItem.quantity+1}) \
                .where(OrderItem.order == order and OrderItem.item == item) \
                .execute()      
            update.message.reply_text("Added another {item_name} to order".format(item_name=item.name))
    except Exception as e:
        logger.debug(e)
        update.message.reply_text("Item not found")


def delete_order(bot, update):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    Order.delete().where((Order.user_id == user_id) & (Order.chat_id == chat_id)).execute()
    update.message.reply_text("Deleted order")


def my_order(bot, update):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    order = Order.select().where((Order.user_id == user_id) & (Order.chat_id == chat_id))
    if order.exists():
        total_price = 0
        text = ""
        for order_item in OrderItem.select().where(OrderItem.order == order):
            text += "{item_name}  <b>x{quantity}</b>\n".format(item_name=order_item.item.name, quantity=order_item.quantity)
            total_price += order_item.item.price * order_item.quantity

        text += "\nTotal price: {total:.2f} €".format(total=total_price)
        update.message.reply_text(text=text, parse_mode=telegram.ParseMode.HTML)
    else:
        update.message.reply_text("You order is empty")


def summary(bot, update):
    chat_id = update.message.chat.id
    items = {}
    for order_item in OrderItem.select(OrderItem, Order).join(Order).where(OrderItem.order.chat_id == chat_id):
        item = order_item.item
        if item in items:
            items[item] += order_item.quantity
        else:
            items[item] = order_item.quantity
    
    if len(items) > 0:
        total_price = 0
        text = ""
        for item in items.keys():
            text += "<b>x{quantity}</b>  <i>{item_name}</i>\n".format(item_name=item.name, quantity=items[item])
            total_price += item.price * items[item]

        text += "\nTotal price: {total:.2f} €".format(total=total_price)
        update.message.reply_text(text=text, parse_mode=telegram.ParseMode.HTML)
    else:
        update.message.reply_text("No order created yet")


def listorders(bot, update):
    chat_id = update.message.chat.id
    text = ""
    for order in Order.select().where(Order.chat_id == chat_id):
        username = order.username
        total_price = 0
        text += "<b>{username}</b>:\n".format(username=username)
        for order_item in OrderItem.select().where(OrderItem.order == order):
            text += "<i>{name}</i> <b>x{quantity}</b>  ".format(name=order_item.item.name, quantity=order_item.quantity)
            total_price += order_item.item.price * order_item.quantity

        text += "\n<b>{total:.2f}</b> €\n\n".format(total=total_price)
        
    update.message.reply_text(text=text, parse_mode=telegram.ParseMode.HTML)


def restaurants(bot, update):
    current_page = int(update.callback_query.data.split("_")[1]) if update.callback_query else 1

    all_restaurants = Restaurant.select()
    total_pages = math.ceil(len(all_restaurants)/RESTAURANT_PER_PAGE)
    
    if total_pages > 1:
        from_item = (current_page*RESTAURANT_PER_PAGE) - RESTAURANT_PER_PAGE
        to_item = current_page*RESTAURANT_PER_PAGE
        keyboard = []
        for r in all_restaurants[from_item:to_item]:
            keyboard.append(
                [InlineKeyboardButton(c.name, callback_data="restaurant_{restaurant_id}_1".format(restaurant_id=r.id))]
            )

        keyboard.append(navigation_buttons("restaurants", current_page, total_pages))
    else:
        keyboard = []
        for c in all_restaurants:
            keyboard.append(
                [InlineKeyboardButton(c.name, callback_data="restaurant_{restaurant_id}_1".format(restaurant_id=r.id))]
            )

    if update.callback_query:
        update.callback_query.edit_message_text(text="Seleziona un ristorante:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text(text="Seleziona un ristorante:", reply_markup=InlineKeyboardMarkup(keyboard))


bot.dispatcher.add_handler(CallbackQueryHandler(categories, pattern="^categories_[\d]+$"))
bot.dispatcher.add_handler(CallbackQueryHandler(category, pattern="^category_[\d]+_[\d]+$"))
bot.dispatcher.add_handler(RegexHandler('^/order_[\d]+$', order))
bot.dispatcher.add_handler(RegexHandler('^/order_[\d]+@[a-zA-Z0-9]+$', order))
bot.dispatcher.add_handler(CommandHandler('menu', categories))
bot.dispatcher.add_handler(CommandHandler('deleteorder', delete_order))
bot.dispatcher.add_handler(CommandHandler('myorder', my_order))
bot.dispatcher.add_handler(CommandHandler('summary', summary))
bot.dispatcher.add_handler(CommandHandler('listorders', listorders))

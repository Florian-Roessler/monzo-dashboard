import numpy as np
import requests
import pandas as pd
import re
import argparse
import os


re_postcode = re.compile("(([gG][iI][rR] {0,}0[aA]{2})|((([a-pr-uwyzA-PR-UWYZ][a-hk-yA-HK-Y]?[0-9][0-9]?)|(([a-pr-uwyzA-PR-UWYZ][0-9][a-hjkstuwA-HJKSTUW])|([a-pr-uwyzA-PR-UWYZ][a-hk-yA-HK-Y][0-9][abehmnprv-yABEHMNPRV-Y]))) {0,}[0-9][abd-hjlnp-uw-zABD-HJLNP-UW-Z]{2}))")


def main(MONZO_FILE):
    df = pd.read_csv(MONZO_FILE)
    # set correct index and transform to datetime
    df.set_index("created", inplace=True)
    df.index = pd.to_datetime(df.index)
    df.drop(["id"], inplace=True, axis=1)

    # Take out the colons in the amounts
    df.loc[:, "local_amount"] = df["local_amount"].str.replace(",", "")
    df.loc[:, "amount"] = df["amount"].str.replace(",", "")

    # Convert dtypes to float
    df.loc[:, ["local_amount", "amount"]] = df[["local_amount",
                                                "amount"]].astype(float)

    # add a cumulative sum to the dataframe
    df["cumsum"] = df["amount"].cumsum()
    # Fill unknown decription with category
    df["description"].fillna(df["category"], inplace=True)
    # convert the cells in which uk postcodes were found
    df["uk_postcode"] = df["address"].apply(
            lambda x: re_postcode.findall(str(x))[0][0]
            if re_postcode.search(str(x)) else np.nan)

    # add longitude and latitude colums
    all_postcodes = df["uk_postcode"].dropna().drop_duplicates().tolist()
    # because the api only allows requests containing 100 postcodes we chunk
    postcode_chunks = [all_postcodes[i:i + 100]
                        for i in range(0, len(all_postcodes), 100)]
    # create a lookup dict postcode as keys and lat/long as string value
    lookup = {}
    for chunk in postcode_chunks:
        r = requests.post("https://api.postcodes.io/postcodes",
                          data={"postcodes": chunk})
        for res in r.json()['result']:
            if ((res['query'] not in lookup.keys()) and (res['result']
                                                         is not None)):
                lookup[res['query']] = "%s,%s" % (res['result']['latitude'],
                                                  res['result']['longitude'])
            elif res['result'] is None:
                print("Postcodes not found %s" % res['query'])

    # create two new columns for postcodes
    df['lat'], df['long'] = df['uk_postcode'].replace(
            lookup).str.split(',', 1).str
    df.to_csv("monzo_processed.csv")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("monzo_file",
                        help="specify relative path to monzo csv file here")
    args = parser.parse_args()
    main(os.path.expanduser(args.monzo_file))

from threading import Thread
import random

def run(idd, timm=1):
    import time
    
    sentenses = []
    max_len=0
    for _ in range(timm):
        s = ', '.join(['xin chao']*random.randint(2, 9))
        sentenses.append(s)
        max_len = len(s) if len(s) > max_len else max_len

    return sentenses[0]

def run_time(idd, dup, timee):
    from wkr_serving.client import WKRClient
    import time

    bc = WKRClient(ip='0.0.0.0', check_version=False, port=8066, port_out=8068, ignore_all_checks=True)

    for i in range(timee):
        e = bc.encode(run(idd, dup))
        print("{}\t{}".format(idd, e.shape))

    # def generator():
    #     i = 0
    #     for _ in range(timee):
    #         yield run(idd, bc, dup)
    #         i+=1
    #         time.sleep(random.randint(2, 6))
    #     print('SENT:', idd, 'called:', i)

    # r = 0
    # def receiver(gen):
    #     for res in gen:
    #         e = res.embedding
    #         print("{}\t{}".format(idd, e.shape))

    # output_generator = bc.encode_async(generator(), delay=0.1)

    # while True:
    #     receiver(output_generator)
    #     if bc.pending_request:
    #         pass
    #     else:
    #         time.sleep(0.1)
    #     output_generator = bc.fetch(delay=0.1)

    bc.close()

    print('DONE:', idd, 'called:', r)

def test_ping(idd):
    random_dup = 1#random.randint(1, 6)
    # random_time = random.randint(70, 100)
    random_time = random.randint(2, 3)
    t = Thread(target=run_time, args=(idd, random_dup, random_time))
    t.daemon = True
    t.start()

if __name__ == '__main__':
    import time

    a = 0
    for i in range(4):
        print(i)
        test_ping(a)
        a+=1
    print('\n')

    for i in range(100000):
        time.sleep(50)
        # test_ping(a)
        a+=1